"""Builds the real database once per session through the app's own startup, then shares it."""

from collections.abc import Callable, Iterator
from pathlib import Path

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from casm.api.app import create_app

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
UI_ORIGIN: str = "http://127.0.0.1:9095"


@pytest.fixture(scope="session")
def make_app() -> Callable[[Path], FastAPI]:
    """Factory for the app under test, pointed at the repository's real docs and references."""

    def build(db_path: Path) -> FastAPI:
        return create_app(
            db_path=db_path,
            references_dir=REPO_ROOT / "docs" / "references",
            wiki_dir=REPO_ROOT / "docs" / "wiki",
            index_file=REPO_ROOT / "README.md",
            allowed_origins=[UI_ORIGIN],
        )

    return build


@pytest.fixture(scope="session")
def client(
    make_app: Callable[[Path], FastAPI], tmp_path_factory: pytest.TempPathFactory
) -> Iterator[TestClient]:
    """The app under test. Entering the client runs startup, which rebuilds the database."""
    app: FastAPI = make_app(tmp_path_factory.mktemp("casm") / "casm.db")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def con(client: TestClient) -> Iterator[duckdb.DuckDBPyConnection]:
    """A read-only cursor on the database the app built, for testing the layers below HTTP."""
    cursor: duckdb.DuckDBPyConnection = client.app.state.con.cursor()
    yield cursor
    cursor.close()
