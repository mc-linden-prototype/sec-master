"""The FastAPI app: rebuilds the DuckDB database on launch and serves the versioned JSON API."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from casm.api.errors import NotFoundError
from casm.api.request_logging import RequestLoggingMiddleware
from casm.api.utils.file_utils import file_sha256
from casm.api.v1.reference import endpoints as reference_endpoints
from casm.api.v1.securities import endpoints as securities_endpoints
from casm.api.v1.wiki import endpoints as wiki_endpoints
from casm.db.migrate import MIGRATIONS_DIR, rebuild_database

# (id, label, icon, pinned source file relative to docs/references/master-data, or None)
REFERENCE_SETS: tuple[tuple[str, str, str, str | None], ...] = (
    (
        "venues",
        "Venues (ISO 10383)",
        "account_balance",
        "market-identifier-codes/ISO10383_MIC.xlsx",
    ),
    (
        "gics",
        "GICS Hierarchy",
        "account_tree",
        "gics-classification/Effective+until+March+17+2023.xlsx",
    ),
    ("taxonomy", "Instrument Taxonomy", "category", None),
    (
        "countries",
        "Countries (ISO 3166)",
        "public",
        "iso-country-codes/iso-country-codes.csv",
    ),
    (
        "isda",
        "ISDA Equity Taxonomy",
        "gavel",
        "product-classification-isda/ISDA-Taxonomy_EQ-CR-FX-IR_v2.0__3-_September_2019-FINAL.xls",
    ),
)
logger: logging.Logger = logging.getLogger("casm.api.app")
TAXONOMY_MIGRATION: str = "02_products_taxonomy.sql"


def build_set_meta(*, references_dir: Path) -> list[dict[str, object]]:
    """Describe each reference set's source file and its SHA-256 for the status card."""
    meta: list[dict[str, object]] = []
    for set_id, label, icon, relative in REFERENCE_SETS:
        path: Path = (
            references_dir / "master-data" / relative
            if relative
            else MIGRATIONS_DIR / TAXONOMY_MIGRATION
        )
        meta.append(
            {
                "id": set_id,
                "label": label,
                "icon": icon,
                "file": path.name,
                "sha256": file_sha256(path=path),
            }
        )
    return meta


def create_app(
    *,
    db_path: Path,
    references_dir: Path,
    wiki_dir: Path,
    index_file: Path,
    allowed_origins: list[str],
) -> FastAPI:
    """Build the app.

    On startup the database file is deleted and rebuilt from the migrations (the work of
    `casm/db/migrate.py`), then opened read-only for the routers.

    Args:
        db_path: The DuckDB file to rebuild and serve.
        references_dir: `docs/references`, for the source-file hashes on the Reference Data screen.
        wiki_dir: `docs/wiki`, the wiki pages.
        index_file: `README.md`, shown first in the wiki.
        allowed_origins: Browser origins (the UI's address) that may call the API.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Rebuilding the database at %s from the migrations", db_path)
        started: float = time.perf_counter()
        applied: list[str] = await asyncio.to_thread(rebuild_database, db_path=db_path)
        app.state.con = await asyncio.to_thread(
            duckdb.connect, str(db_path), read_only=True
        )
        app.state.built_at = datetime.now(UTC).isoformat(timespec="seconds")
        app.state.migrations = applied
        logger.info(
            "Database ready: %d migrations applied in %.1f s (%s ... %s)",
            len(applied),
            time.perf_counter() - started,
            applied[0],
            applied[-1],
        )
        try:
            yield
        finally:
            logger.info("Shutting down: closing the database")
            app.state.con.close()

    app: FastAPI = FastAPI(title="C.A.S.M Security Master", lifespan=lifespan)
    app.state.set_meta = build_set_meta(references_dir=references_dir)
    app.state.wiki = {"wiki_dir": wiki_dir, "index_file": index_file}

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(securities_endpoints.router)
    app.include_router(reference_endpoints.router)
    app.include_router(wiki_endpoints.router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "built_at": app.state.built_at,
            "migrations": app.state.migrations,
        }

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app
