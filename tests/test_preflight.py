"""Preflight checks that a fresh machine can run C.A.S.M."""

import socket
import sys
from pathlib import Path

from casm import preflight

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
REFERENCES: Path = REPO_ROOT / "docs" / "references"


def test_python_version_is_accepted() -> None:
    name, ok, detail = preflight.check_python()
    assert ok and f"{sys.version_info.major}.{sys.version_info.minor}" in detail


def test_missing_package_is_reported() -> None:
    results = preflight.check_packages(names=("duckdb", "no_such_package_xyz"))
    assert [ok for _, ok, _ in results] == [True, False]


def test_all_pinned_inputs_are_present() -> None:
    assert all(ok for _, ok, _ in preflight.check_inputs(references_dir=REFERENCES))


def test_missing_inputs_are_reported(tmp_path: Path) -> None:
    assert not any(ok for _, ok, _ in preflight.check_inputs(references_dir=tmp_path))


def test_database_build_matches_the_seed() -> None:
    name, ok, detail = preflight.check_database_build()
    assert ok, detail
    assert "sec_instrument=398" in detail and "ref_mic_registry=2883" in detail


def test_busy_port_is_reported_but_does_not_fail_the_check() -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        name, ok, detail = preflight.check_ports(host="127.0.0.1", ports={"API": port})[0]
    assert ok and "in use by process" in detail and "relaunch" in detail


def test_free_port_is_reported_free() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    assert (
        preflight.check_ports(host="127.0.0.1", ports={"UI": port})[0][2]
        == "free on 127.0.0.1"
    )


def test_run_checks_covers_every_area() -> None:
    results = preflight.run_checks(
        references_dir=REFERENCES, host="127.0.0.1", ports={"API": 1, "UI": 2}
    )
    names = " ".join(name for name, _, _ in results)
    for expected in (
        "Python version",
        "Package fastapi",
        "Pinned input",
        "Database build",
        "Port 1 (API)",
    ):
        assert expected in names
