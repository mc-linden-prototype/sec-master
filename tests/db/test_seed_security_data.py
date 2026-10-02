"""Loads every migration, including the security seed, and checks the seeded sample against the rules."""

from pathlib import Path

import duckdb
import pytest

MIGRATIONS: Path = Path(__file__).parents[2] / "src" / "casm" / "db" / "migrations"
FILING: str = "13F-HR:0001193125-26-350767"
SUBTYPES: tuple[str, ...] = (
    "sec_instrument_eq_spt",
    "sec_instrument_eq_warrant_right",
    "sec_instrument_fi_bond",
)


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    connection: duckdb.DuckDBPyConnection = duckdb.connect()
    for path in sorted(MIGRATIONS.glob("*.sql")):
        connection.execute(path.read_text(encoding="utf-8"))
    return connection


def scalar(*, con: duckdb.DuckDBPyConnection, sql: str) -> int:
    row: tuple[int] | None = con.execute(sql).fetchone()
    assert row is not None
    return row[0]


def test_every_sampled_row_is_an_instrument_or_an_exception(
    con: duckdb.DuckDBPyConnection,
) -> None:
    sampled: int = scalar(
        con=con,
        sql=f"SELECT count(*) FROM sec_identifier_xref WHERE scheme = 'CUSIP' AND source = '{FILING}'",
    )
    queued: int = scalar(con=con, sql="SELECT count(*) FROM sec_exception_queue")
    assert sampled + queued == 301


def test_every_instrument_has_a_listing(con: duckdb.DuckDBPyConnection) -> None:
    """R11."""
    missing: int = scalar(
        con=con,
        sql="SELECT count(*) FROM sec_instrument i "
        "LEFT JOIN sec_listing l USING (instrument_id) WHERE l.listing_id IS NULL",
    )
    assert missing == 0


def test_every_instrument_has_exactly_one_subtype_row(
    con: duckdb.DuckDBPyConnection,
) -> None:
    """R1: the load-time check that the table named by the taxonomy holds the row."""
    union: str = " UNION ALL ".join(
        f"SELECT instrument_id FROM {table}" for table in SUBTYPES
    )
    bad: int = scalar(
        con=con,
        sql=f"SELECT count(*) FROM sec_instrument i LEFT JOIN "
        f"(SELECT instrument_id, count(*) n FROM ({union}) GROUP BY 1) s USING (instrument_id) "
        "WHERE coalesce(s.n, 0) <> 1",
    )
    assert bad == 0


def test_no_instrument_carries_position_data(con: duckdb.DuckDBPyConnection) -> None:
    columns: list[str] = [
        row[0]
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name LIKE 'sec_%'"
        ).fetchall()
    ]
    assert not {
        "market_value",
        "shares",
        "quantity",
        "amount",
        "notional",
        "position",
    } & set(columns)


def test_listing_venues_are_loaded_venues_and_placeholders_are_defaults(
    con: duckdb.DuckDBPyConnection,
) -> None:
    bad: int = scalar(
        con=con,
        sql="SELECT count(*) FROM sec_listing WHERE (mic IN ('XXXX', 'XOFF')) <> (source = 'DEFAULT')",
    )
    assert bad == 0
    assert scalar(con=con, sql="SELECT count(*) FROM sec_v_listing WHERE is_otc") > 0


def test_exceptions_have_reasons(con: duckdb.DuckDBPyConnection) -> None:
    reasons: set[str] = {
        row[0]
        for row in con.execute(
            "SELECT DISTINCT reason_code FROM sec_exception_queue"
        ).fetchall()
    }
    assert reasons == {"INVALID_IDENTIFIER", "ISSUER_UNRESOLVED", "VENUE_UNRESOLVED"}


def test_sequences_continue_after_the_seed(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "INSERT INTO sec_issuer (legal_name, issuer_type, source, as_of) "
        "VALUES ('NEW CO', 'OTHER', 'test', DATE '2026-09-30')"
    )
    assert scalar(con=con, sql="SELECT count(*) FROM sec_issuer") == 214
