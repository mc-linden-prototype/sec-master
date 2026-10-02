"""Data-access helpers shared by the sections: read-only cursors and row dictionaries."""

import logging
import time
from collections.abc import AsyncIterator

import duckdb
from fastapi import Request

from casm.api.utils.json_utils import plain_value

logger: logging.Logger = logging.getLogger(__name__)
Row = dict[str, object]
Connection = duckdb.DuckDBPyConnection


async def get_cursor(request: Request) -> AsyncIterator[Connection]:
    """Async FastAPI dependency: a cursor on the app's read-only connection, closed after the request."""
    cursor: Connection = request.app.state.con.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def fetch_all(
    *, con: Connection, sql: str, params: list[object] | None = None
) -> list[Row]:
    """Run a query and return each row as a dictionary of plain values keyed by column name."""
    started: float = time.perf_counter()
    cursor: Connection = con.execute(sql, params or [])
    names: list[str] = [column[0] for column in cursor.description]
    rows: list[Row] = [
        {name: plain_value(value) for name, value in zip(names, row, strict=True)}
        for row in cursor.fetchall()
    ]
    logger.debug(
        "query rows=%d %.1f ms: %s",
        len(rows),
        (time.perf_counter() - started) * 1000,
        " ".join(sql.split())[:160],
    )
    return rows


def fetch_one(
    *, con: Connection, sql: str, params: list[object] | None = None
) -> Row | None:
    """Return the first row of a query as a dictionary, or None."""
    rows: list[Row] = fetch_all(con=con, sql=sql, params=params)
    return rows[0] if rows else None


def scalar(*, con: Connection, sql: str, params: list[object] | None = None) -> int:
    """Return the single integer a count query produces."""
    row: tuple[int] | None = con.execute(sql, params or []).fetchone()
    return int(row[0]) if row else 0
