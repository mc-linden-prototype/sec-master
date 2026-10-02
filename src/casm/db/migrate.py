"""Applies the SQL migrations in src/casm/db/migrations, in name order, to a DuckDB file.

Run ad hoc: `uv run python src/casm/db/migrate.py [--db PATH]`. It deletes the DuckDB file if it
exists and rebuilds it from scratch, so the result never depends on what was there before.
"""

import argparse
from pathlib import Path

import duckdb

MIGRATIONS_DIR: Path = Path(__file__).parent / "migrations"
DEFAULT_DB: Path = Path(__file__).parent / "casm.db"


class MigrationError(Exception):
    """A migration file could not be applied."""


def apply_migrations(
    *, con: duckdb.DuckDBPyConnection, migrations_dir: Path
) -> list[str]:
    """Run every `*.sql` file in `migrations_dir` in name order.

    Args:
        con: An open DuckDB connection.
        migrations_dir: Folder holding the numbered SQL files.

    Returns:
        The names of the files applied, in order.

    Raises:
        MigrationError: If the folder has no SQL files or a file fails.
    """
    files: list[Path] = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise MigrationError(f"No .sql migration files in {migrations_dir}.")
    for path in files:
        try:
            con.execute(path.read_text(encoding="utf-8"))
        except duckdb.Error as error:
            raise MigrationError(f"Migration {path.name} failed: {error}") from error
    return [path.name for path in files]


def remove_database(*, db_path: Path) -> None:
    """Delete the DuckDB file and its write-ahead log, if present."""
    for path in (db_path, db_path.with_name(db_path.name + ".wal")):
        path.unlink(missing_ok=True)


def rebuild_database(
    *, db_path: Path, migrations_dir: Path = MIGRATIONS_DIR
) -> list[str]:
    """Delete the database file, then create it again by applying every migration.

    Args:
        db_path: The DuckDB file to delete and recreate.
        migrations_dir: Folder holding the numbered SQL files.

    Returns:
        The names of the migrations applied, in order.

    Raises:
        MigrationError: If a migration fails.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    remove_database(db_path=db_path)
    con: duckdb.DuckDBPyConnection = duckdb.connect(str(db_path))
    try:
        return apply_migrations(con=con, migrations_dir=migrations_dir)
    finally:
        con.close()


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB, help="DuckDB file to delete and recreate"
    )
    args: argparse.Namespace = parser.parse_args()
    for name in rebuild_database(db_path=args.db):
        print(f"applied {name}")
    con: duckdb.DuckDBPyConnection = duckdb.connect(str(args.db), read_only=True)
    try:
        counts: list[tuple[str, int]] = [
            (table, con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in (
                "ref_country",
                "ref_venue",
                "ref_product_code",
                "sec_issuer",
                "sec_instrument",
                "sec_listing",
                "sec_exception_queue",
            )
        ]
    finally:
        con.close()
    print(f"database: {args.db}")
    print(", ".join(f"{table}={count}" for table, count in counts))


if __name__ == "__main__":
    main()
