---
name: launch-app
description: Set up a clean Python environment for C.A.S.M and launch the app (API on port 9099, UI on port 9095). Use when someone new wants to install, run, check or stop the app, or hits a setup problem.
---

# Launch C.A.S.M from a clean machine

Assumes only Python is installed. Run every command from the repository root.

## 1. Check Python

```
python --version        # needs 3.12, 3.13 or 3.14
```

On Windows use `py -3 --version` if `python` is not found; on macOS/Linux use `python3`.

## 2. Create and activate a virtual environment

```
python -m venv .venv
```

Activate it:

| Shell | Command |
|---|---|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\activate.bat` |
| macOS / Linux / Git Bash | `source .venv/bin/activate` (Git Bash on Windows: `source .venv/Scripts/activate`) |

## 3. Install the dependencies

```
python -m pip install --upgrade pip uv
uv sync --extra dev
```

`uv sync` reads `pyproject.toml` and `uv.lock` and installs the exact pinned versions (DuckDB, FastAPI,
uvicorn, pydantic, openpyxl, and pytest/black/ruff/httpx for development).

## 4. Confirm the machine is ready

```
uv run python src/main.py --check
```

It prints one `[ok]` or `[FAIL]` line each for: the Python version, every package, every pinned input file
under `docs/references/`, a full database build into a temporary folder (row counts compared with the
seed), and whether ports 9099 and 9095 are free. Expect `Ready to run.` Fix any `FAIL` first.

Optional: `uv run pytest -q` runs the whole test suite (about a minute; all tests should pass).

## 5. Run the app

```
uv run python src/main.py
```

If a copy is already running on 9099 or 9095, the launch **stops that process and relaunches both**. The API then
starts first and **always deletes and rebuilds `src/casm/db/casm.db`** from the SQL migrations
(`src/casm/db/migrations/`), then the UI starts. The terminal prints:

| What | Address |
|---|---|
| Web UI | http://127.0.0.1:9095 |
| API Swagger docs | http://127.0.0.1:9099/docs |
| API ReDoc | http://127.0.0.1:9099/redoc |
| API health | http://127.0.0.1:9099/api/health |

The API writes its log to the console and to `logs/casm-api.log` (rotating, not committed); `--log-level DEBUG`
adds every search and SQL query, and `--no-log-file` keeps it to the console. Every line carries a request id,
which is also returned in the `X-Request-ID` response header.

Stop with Ctrl+C. Ports are 9099 (API, "9-0-9-9") and 9095 (UI); change with `--api-port` and `--ui-port`.

## Rebuild the database without the app

```
uv run python src/casm/db/migrate.py
```

## Troubleshooting

- **A port is in use:** the launch stops whatever holds 9099 and 9095. To keep that process, run on other ports:
  `--api-port 9199 --ui-port 9195`.
- **The UI loads but shows "Could not load this screen":** the API is not running at the address in
  `/config.js`; start both with `src/main.py`, not the UI alone.
- **The page is unstyled or has no icons:** the UI loads Tailwind, fonts, `marked` and `mermaid` from CDNs, so
  it needs internet access.
- **`uv: command not found`:** the virtual environment is not active (step 2), or run `python -m uv ...`.
- **`--check` fails on Python version:** install Python 3.12 to 3.14; `uv` can also fetch one with
  `uv python install 3.13`.
