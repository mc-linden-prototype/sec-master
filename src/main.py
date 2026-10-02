"""Starts C.A.S.M: the API (which rebuilds the database first) on port 9099, then the web UI on 9095.

Run: `uv run python src/main.py`. Use `--check` first to confirm the machine is ready.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import uvicorn

from casm.api.app import create_app
from casm.api.logging_config import configure_logging
from casm.db.migrate import DEFAULT_DB
from casm.ports import free_ports
from casm.preflight import Check, run_checks
from casm.ui.server import create_ui_app

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
REFERENCES_DIR: Path = REPO_ROOT / "docs" / "references"
WIKI_DIR: Path = REPO_ROOT / "docs" / "wiki"
INDEX_FILE: Path = REPO_ROOT / "README.md"
LOG_FILE: Path = REPO_ROOT / "logs" / "casm-api.log"
API_PORT: int = 9099  # 9-0-9-9
UI_PORT: int = 9095  # 9-0-9-5: same family, the UI is the "5" you look at


def print_checks(*, checks: list[Check]) -> bool:
    """Print the preflight results and say whether all passed."""
    for name, ok, detail in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {detail}")
    passed: bool = all(ok for _, ok, _ in checks)
    print("Ready to run." if passed else "Fix the FAIL lines above, then run again.")
    return passed


async def serve(
    *, host: str, api_port: int, ui_port: int, db_path: Path, log_level: str
) -> None:
    """Start the API, wait until its database is built and it is accepting requests, then start the UI."""
    api_url: str = f"http://{host}:{api_port}"
    ui_url: str = f"http://{host}:{ui_port}"
    api_app = create_app(
        db_path=db_path,
        references_dir=REFERENCES_DIR,
        wiki_dir=WIKI_DIR,
        index_file=INDEX_FILE,
        allowed_origins=[ui_url, f"http://localhost:{ui_port}"],
    )
    api_server = uvicorn.Server(
        uvicorn.Config(
            api_app,
            host=host,
            port=api_port,
            log_level=log_level.lower(),
            access_log=False,  # the request middleware logs every request with its id and duration
        )
    )
    ui_server = uvicorn.Server(
        uvicorn.Config(
            create_ui_app(api_url=api_url), host=host, port=ui_port, log_level="warning"
        )
    )
    ui_server.install_signal_handlers = (
        lambda: None
    )  # Ctrl+C stops the API, which then stops the UI
    for port, pid in await asyncio.to_thread(
        free_ports, host=host, ports=[api_port, ui_port]
    ):
        print(
            f"C.A.S.M: port {port} was in use by process {pid}; stopped it to relaunch."
        )
    print(f"C.A.S.M: rebuilding {db_path} from the migrations, then starting the API...")
    api_task = asyncio.create_task(api_server.serve())
    while not api_server.started and not api_task.done():
        await asyncio.sleep(0.1)
    if not api_server.started:
        await api_task
        return
    ui_task = asyncio.create_task(ui_server.serve())
    print(
        "\n  C.A.S.M is running\n"
        f"    UI                : {ui_url}\n"
        f"    API (ReDoc)       : {api_url}/redoc\n"
        "  Press Ctrl+C to stop.\n"
    )
    await api_task
    ui_server.should_exit = True
    await ui_task


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=API_PORT)
    parser.add_argument("--ui-port", type=int, default=UI_PORT)
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB, help="DuckDB file, rebuilt on every launch"
    )
    parser.add_argument(
        "--log-level", default="INFO", help="DEBUG, INFO, WARNING or ERROR"
    )
    parser.add_argument(
        "--log-file", type=Path, default=LOG_FILE, help="rotating log file for the API"
    )
    parser.add_argument(
        "--no-log-file", action="store_true", help="log to the console only"
    )
    parser.add_argument(
        "--check", action="store_true", help="check this machine is ready, then exit"
    )
    args: argparse.Namespace = parser.parse_args()
    if args.check:
        print("C.A.S.M preflight:")
        ports: dict[str, int] = {"API": args.api_port, "UI": args.ui_port}
        checks: list[Check] = run_checks(
            references_dir=REFERENCES_DIR, host=args.host, ports=ports
        )
        sys.exit(0 if print_checks(checks=checks) else 1)
    log_file: Path | None = None if args.no_log_file else args.log_file
    configure_logging(level=args.log_level, log_file=log_file)
    logging.getLogger("casm").info(
        "Logging at %s to the console%s",
        args.log_level.upper(),
        f" and {log_file}" if log_file else "",
    )
    asyncio.run(
        serve(
            host=args.host,
            api_port=args.api_port,
            ui_port=args.ui_port,
            db_path=args.db,
            log_level=args.log_level,
        )
    )


if __name__ == "__main__":
    main()
