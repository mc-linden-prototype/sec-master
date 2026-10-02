"""App wiring: startup rebuild, health, CORS, root redirect and error mapping."""

from collections.abc import Callable
from pathlib import Path

import duckdb
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.api.conftest import UI_ORIGIN  # noqa: F401  (shared constant)


class TestHealth:
    def test_health_lists_the_applied_migrations(self, client: TestClient) -> None:
        body = client.get("/api/health").json()
        assert body["status"] == "ok" and body["built_at"]
        assert body["migrations"][0] == "00_ref_data_schema.sql"
        assert body["migrations"][-1] == "04_seed_security_data.sql"
        assert body["migrations"] == sorted(body["migrations"])


class TestStartupRebuild:
    def test_launch_deletes_the_old_database_and_rebuilds_it(
        self, make_app: Callable[[Path], FastAPI], tmp_path: Path
    ) -> None:
        db = tmp_path / "casm.db"
        stale = duckdb.connect(str(db))
        stale.execute("CREATE TABLE stale (x INTEGER); INSERT INTO stale VALUES (1)")
        stale.close()
        app = make_app(db)
        with TestClient(app) as test_client:
            tables = {
                row[0]
                for row in app.state.con.execute(
                    "SELECT table_name FROM information_schema.tables"
                ).fetchall()
            }
            assert "stale" not in tables and "sec_instrument" in tables
            assert test_client.get("/api/v1/securities").json()["total"] == 398

    def test_launch_creates_a_missing_folder(
        self, make_app: Callable[[Path], FastAPI], tmp_path: Path
    ) -> None:
        db = tmp_path / "nested" / "dir" / "casm.db"
        with TestClient(make_app(db)) as test_client:
            assert test_client.get("/api/health").status_code == 200
        assert db.is_file()

    def test_database_is_read_only_while_serving(self, client: TestClient) -> None:
        try:
            client.app.state.con.execute("DELETE FROM sec_instrument")
        except duckdb.Error:
            pass
        else:  # pragma: no cover
            raise AssertionError("the serving connection must not allow writes")
        assert client.get("/api/v1/securities").json()["total"] == 398


class TestCors:
    def test_the_ui_origin_is_allowed(self, client: TestClient) -> None:
        response = client.get("/api/v1/securities/filters", headers={"Origin": UI_ORIGIN})
        assert response.headers["access-control-allow-origin"] == UI_ORIGIN

    def test_other_origins_get_no_cors_header(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/securities/filters", headers={"Origin": "http://evil.example"}
        )
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_allows_get_only(self, client: TestClient) -> None:
        headers = {"Origin": UI_ORIGIN, "Access-Control-Request-Method": "DELETE"}
        assert client.options("/api/v1/securities", headers=headers).status_code == 400


class TestRoutes:
    def test_root_redirects_to_the_swagger_docs(self, client: TestClient) -> None:
        response = client.get("/", follow_redirects=False)
        assert (
            response.status_code in (302, 307) and response.headers["location"] == "/docs"
        )
        assert client.get("/docs").status_code == 200

    def test_unknown_path_is_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/nope").status_code == 404

    def test_not_found_error_becomes_a_404_json_body(self, client: TestClient) -> None:
        response = client.get("/api/v1/securities/424242")
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "No instrument 424242."}

    def test_openapi_documents_every_section(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        for path in (
            "/api/v1/securities",
            "/api/v1/reference/venues/{mic}",
            "/api/v1/wiki/{page_id}",
        ):
            assert path in paths
