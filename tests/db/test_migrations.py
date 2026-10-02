"""Applies every migration to an in-memory DuckDB and checks the venue and listing rules."""

from pathlib import Path

import duckdb
import pytest

MIGRATIONS: Path = Path(__file__).parents[2] / "src" / "casm" / "db" / "migrations"
SECURITY_SEED: str = (
    "04_seed_security_data.sql"  # excluded: these tests start from an empty security schema
)


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    connection: duckdb.DuckDBPyConnection = duckdb.connect()
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name == SECURITY_SEED:
            continue
        connection.execute(path.read_text(encoding="utf-8"))
    connection.execute(
        "INSERT INTO sec_issuer (legal_name, issuer_type, source, as_of) "
        "VALUES ('ACME CORP', 'OPERATING_COMPANY', 'test', DATE '2026-06-30')"
    )
    for name in ("ACME COM", "ACME PREF"):
        connection.execute(
            "INSERT INTO sec_instrument (product_code, issuer_id, security_name, source, as_of) "
            "SELECT 'EQ-SPT-COMMON', issuer_id, ?, 'test', DATE '2026-06-30' FROM sec_issuer",
            [name],
        )
    return connection


def add_listing(
    *,
    con: duckdb.DuckDBPyConnection,
    instrument_id: int,
    mic: str,
    is_primary: bool = False,
    source: str = "OPENFIGI",
    confidence: str = "HIGH",
) -> None:
    con.execute(
        "INSERT INTO sec_listing (instrument_id, mic, primary_marker, source, as_of, confidence) "
        "VALUES (?, ?, ?, ?, DATE '2026-09-30', ?)",
        [instrument_id, mic, 1 if is_primary else None, source, confidence],
    )


def test_registry_and_venue_seed(con: duckdb.DuckDBPyConnection) -> None:
    assert con.execute("SELECT count(*) FROM ref_mic_registry").fetchone() == (2883,)
    assert con.execute("SELECT count(*) FROM ref_venue").fetchone() == (13,)
    types: dict[str, str] = dict(
        con.execute("SELECT mic, venue_type FROM ref_venue").fetchall()
    )
    assert (
        types["XNYS"] == "EXCHANGE" and types["XXXX"] == "NONE" and types["XOFF"] == "OTC"
    )


def test_venue_mic_must_be_in_registry(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        con.execute(
            "INSERT INTO ref_venue (mic, operating_mic, name, venue_type) "
            "VALUES ('QQQQ', 'QQQQ', 'NOT IN REGISTRY', 'EXCHANGE')"
        )


def test_listing_unknown_venue_rejected(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_listing(
            con=con, instrument_id=1, mic="XLON"
        )  # in the registry, not a loaded venue


def test_one_listing_per_instrument_per_venue(con: duckdb.DuckDBPyConnection) -> None:
    add_listing(con=con, instrument_id=1, mic="XNAS")
    add_listing(con=con, instrument_id=1, mic="XNYS")
    with pytest.raises(duckdb.ConstraintException):
        add_listing(con=con, instrument_id=1, mic="XNAS")


def test_at_most_one_primary_listing(con: duckdb.DuckDBPyConnection) -> None:
    add_listing(con=con, instrument_id=1, mic="XNAS", is_primary=True)
    add_listing(con=con, instrument_id=1, mic="XNYS")
    add_listing(con=con, instrument_id=1, mic="ARCX")
    add_listing(con=con, instrument_id=2, mic="XNAS", is_primary=True)
    with pytest.raises(duckdb.ConstraintException):
        add_listing(con=con, instrument_id=1, mic="BATS", is_primary=True)


def test_placeholder_listings_are_defaults(con: duckdb.DuckDBPyConnection) -> None:
    add_listing(con=con, instrument_id=1, mic="XXXX", source="DEFAULT", confidence="LOW")
    with pytest.raises(duckdb.ConstraintException):
        add_listing(
            con=con, instrument_id=2, mic="XOFF", source="OPENFIGI", confidence="LOW"
        )
    with pytest.raises(duckdb.ConstraintException):
        add_listing(
            con=con, instrument_id=2, mic="XOFF", source="DEFAULT", confidence="HIGH"
        )
    with pytest.raises(duckdb.ConstraintException):
        add_listing(
            con=con, instrument_id=2, mic="XNYS", source="DEFAULT", confidence="LOW"
        )


def test_otc_is_derived_from_venue(con: duckdb.DuckDBPyConnection) -> None:
    add_listing(con=con, instrument_id=1, mic="XNYS")
    add_listing(con=con, instrument_id=2, mic="XOFF", source="DEFAULT", confidence="LOW")
    flags: dict[int, bool] = dict(
        con.execute("SELECT instrument_id, is_otc FROM sec_v_listing").fetchall()
    )
    assert flags == {1: False, 2: True}


def test_every_instrument_has_a_listing(con: duckdb.DuckDBPyConnection) -> None:
    """R11 is a load-time check: this is the query the loader runs."""
    query: str = (
        "SELECT i.instrument_id FROM sec_instrument i "
        "LEFT JOIN sec_listing l USING (instrument_id) WHERE l.listing_id IS NULL"
    )
    assert len(con.execute(query).fetchall()) == 2
    add_listing(con=con, instrument_id=1, mic="XNAS")
    add_listing(con=con, instrument_id=2, mic="XXXX", source="DEFAULT", confidence="LOW")
    assert con.execute(query).fetchall() == []


def test_ticker_is_not_an_instrument_identifier(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        con.execute(
            "INSERT INTO sec_identifier_xref (instrument_id, scheme, value, source, as_of) "
            "VALUES (1, 'TICKER', 'ACME', 'test', DATE '2026-06-30')"
        )
