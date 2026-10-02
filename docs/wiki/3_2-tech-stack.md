---
name: tech-stack
description: The technology stack of C.A.S.M, the monorepo layout, the ports, the async model, how to set up from a clean machine with only Python installed, and the commands to run, check and test it.
---

# Tech Stack and Setup

> Index: [README.md](../../README.md) · Database: [Database schema](3_1-database-schema.md) · API and UI: [API and UI](3_3-api-ui.md)

## 1. Stack

| Layer | Choice | Version (pinned in `uv.lock`) | Why |
|---|---|---|---|
| Language | Python | 3.12 to 3.14 (`requires-python >=3.12,<3.15`) | One language for database loading, API and tests |
| Environment and installs | `uv` | any recent | Reads `pyproject.toml` and `uv.lock`; the lock makes every install identical |
| Database | DuckDB (file `src/casm/db/casm.db`) | 2.0.0 dev build | In-process, no server; real foreign keys, `CHECK` and unique constraints |
| API | FastAPI on Starlette, served by uvicorn | 0.142 / 1.7 / 0.54 | Async routes, typed request models, free Swagger docs |
| Validation | pydantic | 2.14 beta | Request models in `api/v1/models.py` |
| Input files | openpyxl | 3.1 | Reads the pinned Excel inputs used to build the seed |
| Web UI | Plain HTML, CSS and ES modules, no build step | n/a | The prototype's Carbon-style design, kept simple |
| UI libraries (from CDNs) | Tailwind CSS (with typography), `marked`, `mermaid`, IBM Plex Sans, JetBrains Mono, Material Symbols | latest of the major pinned in `index.html` | Styling, markdown and diagram rendering for the Wiki tab |
| Tests | pytest, httpx (Starlette's test client) | 9.1 / 0.28 | Real database, no mocks, no network |
| Formatting and lint | black, ruff | 26.5 / 0.16 | `uv run black .` and `uv run ruff check --fix .` |

`pyproject.toml` sets `prerelease = "allow"`, so the lock holds DuckDB and pydantic pre-releases; `uv sync`
installs exactly those.

## 2. Monorepo

One repository, one environment, one command to run everything.

| Path | Contents |
|---|---|
| `src/main.py` | Entry point and `--check` |
| `src/casm/db/` | Migrations and `migrate.py` ([Database schema](3_1-database-schema.md)) |
| `src/casm/api/` | The API ([API and UI](3_3-api-ui.md)) |
| `src/casm/ui/` | The web UI and its server ([API and UI](3_3-api-ui.md)) |
| `src/casm/preflight.py` | The environment check |
| `tests/` | Mirrors `src/casm/` |
| `docs/wiki/` | This wiki, indexed by the root `README.md` |
| `docs/references/` | Pinned inputs: the 13F filing, ISO, GICS and ISDA files, and the OpenFIGI, Nasdaq Trader and SEC snapshots |
| `docs/validation/` | The UI validation report and screenshots |
| `.prototype/` | The design prototype and design notes the UI follows |
| `.claude/skills/` | `launch-app`, `explain-casm`, `validate-ui` |

## 3. Ports and processes

| Process | Port | Address |
|---|---|---|
| API (FastAPI, Swagger at `/docs`, ReDoc at `/redoc`) | 9099 | http://127.0.0.1:9099 |
| UI (static files and `config.js`) | 9095 | http://127.0.0.1:9095 |

Both ports start with 909 so they read as one family: 9099 for the API, 9095 for the page you look at.
`src/main.py` runs both servers in one process on one event loop. It starts the API first; the API's startup
deletes `casm.db` and rebuilds it from the migrations, and only when the API is accepting requests does the
UI start and the links print. The UI server writes `/config.js` with the API address, and the API allows that
UI origin through CORS (GET only).

## 4. Async model

The API is async end to end: the app startup, the cursor dependency, every route and the UI server's config
route are `async def`. The DuckDB driver is synchronous, so database and file work stays synchronous in
`service.py` and `queries.py` and each route runs it with `asyncio.to_thread`. The event loop is never blocked
by a query or a file read.

## 5. Set up from a clean machine

Needs only Python 3.12 to 3.14 and internet access (to install packages, and for the UI's CDN libraries).

1. Check that Python 3.12 to 3.14 is installed (on Windows use `py -3 --version`, on macOS or Linux `python3`).

   ```
   python --version
   ```

2. Install uv.

   ```
   python -m pip install --upgrade pip uv
   ```

3. Change to the repository root, the folder holding `pyproject.toml`. The virtual environment is created in the current working directory, so stay here for every remaining step.

   ```
   cd <path-to>/sec-master
   ```

4. Create the virtual environment in that directory.

   ```
   uv venv .venv
   ```

5. Activate it (pick your shell).

   ```
   .venv\Scripts\Activate.ps1          # Windows PowerShell
   .venv\Scripts\activate.bat          # Windows cmd
   source .venv/bin/activate           # macOS, Linux
   source .venv/Scripts/activate       # Git Bash on Windows
   ```

6. Install the packages.

   ```
   uv sync --extra dev
   ```

7. Confirm the machine is ready.

   ```
   uv run python src/main.py --check
   ```

   Each line is `[ok]` or `[FAIL]`: Python version, every package, every pinned input file, a full database build in a temporary folder compared with the seed row counts, and whether ports 9099 and 9095 are free. It ends with `Ready to run.` when everything passes.

8. Run the app, then open the UI and the Swagger docs from the addresses it prints.

   ```
   uv run python src/main.py
   ```

9. Run the tests (optional).

   ```
   uv run pytest -q
   ```

Stop with Ctrl+C. Change ports with `--api-port` and `--ui-port`, the host with `--host`, the database file with `--db`,
and the API log with `--log-level` (default `INFO`), `--log-file` (default `logs/casm-api.log`) or `--no-log-file`.
Log format and levels: [API and UI](3_3-api-ui.md) section 6.

## 6. Commands

| Task | Command |
|---|---|
| Run the app (API then UI) | `uv run python src/main.py` |
| Check the machine | `uv run python src/main.py --check` |
| Rebuild only the database | `uv run python src/casm/db/migrate.py` |
| Test | `uv run pytest -q` |
| Format and lint | `uv run black .` and `uv run ruff check --fix .` |
| Validate the UI in Chrome | `uv run --with playwright python .claude/skills/validate-ui/validate_ui.py` |

## 7. Known gaps

- The UI needs internet access for its CDN libraries and fonts; there is no bundled or offline copy.
- No container image, no CI, no hosted deployment; the database is a local file rebuilt on every launch.
- No authentication: the API is read-only and bound to `127.0.0.1` by default.
- The `uv.lock` holds pre-release DuckDB and pydantic builds.
