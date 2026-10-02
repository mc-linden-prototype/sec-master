"""Checks a fresh machine can run C.A.S.M: Python version, packages, pinned inputs, a database build, ports."""

import importlib.util
import sys
import tempfile
from pathlib import Path

import duckdb

from casm.db.migrate import MIGRATIONS_DIR, rebuild_database
from casm.ports import listening_pids, port_is_free

MIN_PYTHON: tuple[int, int] = (3, 12)
MAX_PYTHON_EXCLUSIVE: tuple[int, int] = (3, 15)
REQUIRED_PACKAGES: tuple[str, ...] = (
    "duckdb",
    "fastapi",
    "uvicorn",
    "pydantic",
    "openpyxl",
)
DEV_PACKAGES: tuple[str, ...] = ("pytest", "httpx")
REQUIRED_INPUTS: tuple[str, ...] = (
    "master-data/iso-country-codes/iso-country-codes.csv",
    "master-data/market-identifier-codes/ISO10383_MIC.xlsx",
    "master-data/gics-classification/Effective+until+March+17+2023.xlsx",
    "linden-sec-filings/holdings/13F-HR-56990.xml",
    "security-data/sample-selection.csv",
)
EXPECTED_COUNTS: dict[str, int] = {
    "ref_country": 249,
    "ref_mic_registry": 2883,
    "ref_product_code": 17,
    "sec_instrument": 398,
}

Check = tuple[str, bool, str]  # (what was checked, passed, detail)


def check_python() -> Check:
    found: tuple[int, int] = sys.version_info[:2]
    ok: bool = MIN_PYTHON <= found < MAX_PYTHON_EXCLUSIVE
    return ("Python version", ok, f"{found[0]}.{found[1]} (need >=3.12,<3.15)")


def check_packages(*, names: tuple[str, ...]) -> list[Check]:
    return [
        (f"Package {name}", importlib.util.find_spec(name) is not None, "importable")
        for name in names
    ]


def check_inputs(*, references_dir: Path) -> list[Check]:
    return [
        (f"Pinned input {relative}", (references_dir / relative).is_file(), "found")
        for relative in REQUIRED_INPUTS
    ]


def check_database_build() -> Check:
    """Build the database in a temporary folder and compare row counts with the seed."""
    with tempfile.TemporaryDirectory() as folder:
        db_path: Path = Path(folder) / "check.db"
        try:
            applied: list[str] = rebuild_database(
                db_path=db_path, migrations_dir=MIGRATIONS_DIR
            )
            con: duckdb.DuckDBPyConnection = duckdb.connect(str(db_path), read_only=True)
            try:
                counts: dict[str, int] = {
                    table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    for table in EXPECTED_COUNTS
                }
            finally:
                con.close()
        except Exception as error:  # a failed build is reported, not raised
            return ("Database build", False, str(error))
    return (
        "Database build",
        counts == EXPECTED_COUNTS,
        f"{len(applied)} migrations applied; "
        + ", ".join(f"{k}={v}" for k, v in counts.items()),
    )


def check_ports(*, host: str, ports: dict[str, int]) -> list[Check]:
    """A busy port is not a failure: launching stops whatever holds it and relaunches."""
    checks: list[Check] = []
    for label, port in ports.items():
        if port_is_free(host=host, port=port):
            checks.append((f"Port {port} ({label})", True, f"free on {host}"))
        else:
            pids: str = (
                ", ".join(str(pid) for pid in listening_pids(port=port)) or "unknown"
            )
            checks.append(
                (
                    f"Port {port} ({label})",
                    True,
                    f"in use by process {pids}; launching will stop it and relaunch",
                )
            )
    return checks


def run_checks(*, references_dir: Path, host: str, ports: dict[str, int]) -> list[Check]:
    """Run every preflight check.

    Args:
        references_dir: The repository's `docs/references`.
        host: The address the servers will bind.
        ports: Label to port for each server.
    """
    return [
        check_python(),
        *check_packages(names=REQUIRED_PACKAGES),
        *check_packages(names=DEV_PACKAGES),
        *check_inputs(references_dir=references_dir),
        check_database_build(),
        *check_ports(host=host, ports=ports),
    ]
