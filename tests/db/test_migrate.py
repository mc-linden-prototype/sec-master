"""Re-running the migrations leaves the same data, and each seed file can be re-run alone."""

from pathlib import Path

import duckdb

from casm.db.migrate import MIGRATIONS_DIR, apply_migrations, remove_database

TABLES: tuple[str, ...] = (
    "ref_country",
    "ref_gics",
    "ref_isda_equity_taxonomy",
    "ref_mic_registry",
    "ref_venue",
    "ref_product_code",
    "sec_issuer",
    "sec_instrument",
    "sec_identifier_xref",
    "sec_listing",
    "sec_exception_queue",
)
SEED_FILES: tuple[str, ...] = (
    "02_products_taxonomy.sql",
    "02_seed_ref_data.sql",
    "03_seed_venues.sql",
    "04_seed_security_data.sql",
)


def counts(*, con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    result: dict[str, int] = {}
    for table in TABLES:
        row: tuple[int] | None = con.execute(f"SELECT count(*) FROM {table}").fetchone()
        assert row is not None
        result[table] = row[0]
    return result


def test_migrations_apply_in_name_order() -> None:
    con: duckdb.DuckDBPyConnection = duckdb.connect()
    names: list[str] = apply_migrations(con=con, migrations_dir=MIGRATIONS_DIR)
    assert names == sorted(names)
    assert (
        names[0] == "00_ref_data_schema.sql" and names[-1] == "04_seed_security_data.sql"
    )


def test_running_all_migrations_twice_gives_the_same_data() -> None:
    con: duckdb.DuckDBPyConnection = duckdb.connect()
    apply_migrations(con=con, migrations_dir=MIGRATIONS_DIR)
    first: dict[str, int] = counts(con=con)
    apply_migrations(con=con, migrations_dir=MIGRATIONS_DIR)
    assert counts(con=con) == first
    assert first["sec_instrument"] == 398 and first["ref_mic_registry"] == 2883


def test_each_seed_file_reruns_alone_and_clears_its_dependents() -> None:
    con: duckdb.DuckDBPyConnection = duckdb.connect()
    apply_migrations(con=con, migrations_dir=MIGRATIONS_DIR)
    for name in SEED_FILES:
        con.execute((MIGRATIONS_DIR / name).read_text(encoding="utf-8"))
    # the last seed file reloads the security data that the earlier ones cleared
    assert counts(con=con)["sec_instrument"] == 398


def test_remove_database_deletes_file_and_wal(tmp_path: Path) -> None:
    db: Path = tmp_path / "casm.db"
    wal: Path = tmp_path / "casm.db.wal"
    db.write_bytes(b"old")
    wal.write_bytes(b"old")
    remove_database(db_path=db)
    assert not db.exists() and not wal.exists()
    remove_database(db_path=db)  # nothing to delete is not an error
