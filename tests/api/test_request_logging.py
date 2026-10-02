"""Request logging: one line per request, request ids, failures, and logs from the layers below."""

import asyncio
import logging
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from casm.api.logging_config import request_id_var

REQUEST_LOGGER = "casm.api.request"


def request_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == REQUEST_LOGGER]


class TestOneLinePerRequest:
    def test_status_and_duration_are_logged_at_info(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=REQUEST_LOGGER):
            client.get("/api/v1/securities/filters")
        (record,) = request_records(caplog)
        assert record.levelno == logging.INFO
        assert re.fullmatch(
            r"GET /api/v1/securities/filters -> 200 \(\d+\.\d ms\)", record.getMessage()
        )

    def test_the_query_string_is_part_of_the_line(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=REQUEST_LOGGER):
            client.get("/api/v1/securities", params={"q": "55306NAB0", "scope": "cusip"})
        assert (
            "/api/v1/securities?q=55306NAB0&scope=cusip -> 200"
            in request_records(caplog)[0].getMessage()
        )

    @pytest.mark.parametrize(
        "path, status",
        [
            ("/api/v1/securities/999999", 404),
            ("/api/v1/securities/abc", 422),
            ("/api/v1/nope", 404),
        ],
    )
    def test_client_errors_are_warnings(
        self, client: TestClient, caplog: pytest.LogCaptureFixture, path: str, status: int
    ) -> None:
        with caplog.at_level(logging.INFO, logger=REQUEST_LOGGER):
            client.get(path)
        (record,) = request_records(caplog)
        assert record.levelno == logging.WARNING and f"-> {status}" in record.getMessage()


class TestRequestId:
    def test_one_is_generated_and_returned(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert re.fullmatch(r"[0-9a-f]{12}", response.headers["x-request-id"])

    def test_each_request_gets_its_own(self, client: TestClient) -> None:
        ids = {client.get("/api/health").headers["x-request-id"] for _ in range(5)}
        assert len(ids) == 5

    def test_the_callers_id_is_kept_so_a_trace_can_be_followed(
        self, client: TestClient
    ) -> None:
        response = client.get(
            "/api/health", headers={"X-Request-ID": "trace-from-the-caller"}
        )
        assert response.headers["x-request-id"] == "trace-from-the-caller"

    def test_an_overlong_id_is_cut(self, client: TestClient) -> None:
        response = client.get("/api/health", headers={"X-Request-ID": "x" * 500})
        assert response.headers["x-request-id"] == "x" * 64

    def test_error_responses_carry_the_id_too(self, client: TestClient) -> None:
        response = client.get("/api/v1/securities/999999")
        assert response.status_code == 404 and response.headers["x-request-id"]

    def test_the_id_is_gone_once_the_request_ends(self, client: TestClient) -> None:
        client.get("/api/health", headers={"X-Request-ID": "short-lived"})
        assert request_id_var.get() == "-"


class TestFailures:
    @pytest.fixture
    def failing_client(
        self, make_app: Callable[[Path], FastAPI], tmp_path: Path
    ) -> TestClient:
        app = make_app(tmp_path / "casm.db")

        @app.get("/boom")
        async def boom() -> None:
            raise RuntimeError("kaboom")

        @app.get("/seen-in-thread")
        async def seen_in_thread() -> dict[str, str]:
            return {"seen": await asyncio.to_thread(request_id_var.get)}

        with TestClient(app) as test_client:
            yield test_client

    def test_an_unhandled_error_is_a_json_500_with_the_request_id_and_no_internals(
        self, failing_client: TestClient
    ) -> None:
        response = failing_client.get("/boom", headers={"X-Request-ID": "boom-1"})
        assert response.status_code == 500
        assert response.json() == {
            "detail": "Internal server error",
            "request_id": "boom-1",
        }
        assert "kaboom" not in response.text and "Traceback" not in response.text
        assert response.headers["x-request-id"] == "boom-1"

    def test_the_failure_is_logged_at_error_with_the_traceback(
        self, failing_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=REQUEST_LOGGER):
            failing_client.get("/boom")
        (record,) = request_records(caplog)
        assert (
            record.levelno == logging.ERROR
            and "GET /boom -> 500 unhandled error" in record.getMessage()
        )
        assert record.exc_info is not None and "kaboom" in str(record.exc_info[1])

    def test_the_app_keeps_serving_after_a_failure(
        self, failing_client: TestClient
    ) -> None:
        failing_client.get("/boom")
        assert failing_client.get("/api/health").status_code == 200

    def test_the_request_id_follows_the_request_into_worker_threads(
        self, failing_client: TestClient
    ) -> None:
        response = failing_client.get(
            "/seen-in-thread", headers={"X-Request-ID": "thread-1"}
        )
        assert response.json() == {"seen": "thread-1"}


class TestLogsFromTheLayersBelow:
    def test_startup_logs_the_rebuild_and_the_result(
        self,
        make_app: Callable[[Path], FastAPI],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.INFO, logger="casm.api.app"):
            with TestClient(make_app(tmp_path / "casm.db")):
                pass
        messages = [r.getMessage() for r in caplog.records if r.name == "casm.api.app"]
        assert any(m.startswith("Rebuilding the database at") for m in messages)
        assert any(
            "Database ready: 6 migrations applied" in m and "00_ref_data_schema.sql" in m
            for m in messages
        )
        assert any(m.startswith("Shutting down") for m in messages)

    def test_a_search_is_logged_at_debug_with_its_parameters_and_row_count(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="casm.api.v1.securities.service"):
            client.get("/api/v1/securities", params={"q": "55306NAB0"})
        (message,) = [
            r.getMessage()
            for r in caplog.records
            if r.name == "casm.api.v1.securities.service"
        ]
        assert "q='55306NAB0'" in message and "-> 1 rows" in message

    def test_a_missing_record_is_logged_at_info(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="casm.api.v1.securities.service"):
            client.get("/api/v1/securities/999999")
        assert any(
            r.getMessage() == "instrument 999999 not found" for r in caplog.records
        )

    def test_every_query_is_timed_at_debug(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="casm.api.utils.database_utils"):
            client.get("/api/v1/securities/filters")
        queries = [
            r.getMessage()
            for r in caplog.records
            if r.name == "casm.api.utils.database_utils"
        ]
        assert queries and all(
            re.match(r"query rows=\d+ \d+\.\d ms: ", m) for m in queries
        )

    def test_nothing_chatty_is_logged_at_info_below_the_request_line(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="casm"):
            client.get("/api/v1/securities/filters")
        assert [r.name for r in caplog.records] == [REQUEST_LOGGER]
