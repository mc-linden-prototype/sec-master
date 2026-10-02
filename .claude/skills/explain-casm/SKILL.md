---
name: explain-casm
description: Teach someone new what C.A.S.M is, what purpose it serves, how the repository is organised and how to find things in the code, data and docs. Use for onboarding, "what does this do", "where is X" and "how does the system fit together" questions.
---

# Explain C.A.S.M and how to navigate it

## What it is and why it exists

C.A.S.M (Cross Asset Security Master) is a **security master**: reference data only, meaning what a
security *is*, never what is owned (no positions, quantities, values or exposure). The Phase 1 prototype
shows that a security master built on a taxonomy, separate issuers and instruments, enforced relationships
and one identifier model works. It uses a Linden Advisors 13F-HR filing purely as a realistic sample list of
instruments (301 of 638 rows) and enriches them from OpenFIGI, Nasdaq Trader, SEC EDGAR and ISO files.

The seven tenets (T1 taxonomy spine, T2 entities vs instruments, T3 integrity by foreign keys, T4 regulatory
attributes, T5 one identifier model, T6 semantic precision, T7 desk alignment) and the integrity rules R1 to
R13 are in `docs/wiki/1_3-project-scope.md` and `3_1-database-schema.md`.

## How to teach it (in this order)

1. **Start with the root `README.md`.** It is the front door: what the system is, the quick start, the monorepo
   map, these skills, the wiki reading order, the seed data sources and the known gaps. Then follow its reading
   order through the wiki (UI tab **Wiki**, or `docs/wiki/`): introduction (1_0), operating model (1_1),
   project scope (1_3), data sources (2_0), classification (2_1), taxonomy (2_2), database (3_1),
   tech stack (3_2), API and UI (3_3).
2. Show the data: UI **Securities** tab (the 398 instruments, their issuers and the exception queue, one inspector
   per row, with the underlying security linked and a breadcrumb trail) and **Reference Data** tab (venues,
   GICS, taxonomy, countries, ISDA). No grid is paged.
3. Show the gaps and sources: an instrument's **Governance** tab lists the attributes not held (ISIN, SEDOL,
   GICS, LEI) and why, and **Lineage** names the source of every datapoint. The integrity rules R1 to R13 are
   in the database and the wiki (`3_1-database-schema.md`), and their tests are in `tests/db/`.
4. Show the code path for one request (below).

## The monorepo map

| Path | What lives there |
|---|---|
| `src/main.py` | Entry point: rebuilds the database, starts the API (9099) and the UI (9095); `--check` preflight |
| `src/casm/db/` | SQL migrations (`migrations/00` to `04`) and `migrate.py`, which deletes and rebuilds `casm.db` |
| `src/casm/api/` | FastAPI app (`app.py`), shared `utils/`, `errors.py`, request logging (`logging_config.py`, `request_logging.py`); versioned routes in `v1/` |
| `src/casm/api/v1/<section>/` | `endpoints.py` (HTTP), `service.py` (logic), `queries.py` (SQL): `securities` (instruments and issuers), `reference`, `wiki` |
| `src/casm/api/v1/models.py` | Pydantic request models (validated query strings) |
| `src/casm/ui/` | Static web UI (`index.html`, `js/`) and `server.py` that serves it |
| `src/casm/preflight.py`, `src/casm/ports.py` | The `--check` environment verification; stopping a previous run before a launch |
| `tests/` | Mirrors `src/casm/`; real in-memory or rebuilt DuckDB, no mocks, no network |
| `docs/wiki/` | The wiki; `README.md` at the root is its index |
| `docs/references/` | Pinned, read-only input data with `source.txt` provenance (filing, ISO, GICS, ISDA, OpenFIGI, SEC) |
| `.prototype/` | The design prototype the UI copies (Carbon-style) |
| `.claude/skills/` | These skills: `launch-app`, `explain-casm`, `validate-ui` |

## Follow one request through the code

`Securities` search box -> `src/casm/ui/js/securities.js` -> `GET /api/v1/securities?q=...` (all matches, never paged) ->
`api/v1/securities/endpoints.py` (validates with `SecuritySearch` in `models.py`, runs the service in a
thread) -> `service.py` (detects the identifier type, adds notes) -> `queries.py` (SQL on `sec_instrument`,
`sec_listing`, `sec_identifier_xref`) -> DuckDB `casm.db`.

## Where to find an answer

| Question | Look in |
|---|---|
| What tables exist and why | `docs/wiki/3_1-database-schema.md`, `src/casm/db/migrations/` |
| Which product codes exist | `docs/wiki/2_1`/`2_2`, `02_products_taxonomy.sql` |
| Where did a datapoint come from | `docs/wiki/2_0-data-sources.md`, project scope section 8.2, the instrument's Lineage tab, `docs/references/security-data/*/source.txt` |
| What is deliberately missing | Known gaps in `README.md` |
| How to run or verify it | skills `launch-app` and `validate-ui` |

## Ground rules to pass on

Phase 1 scope only (17 product codes); nothing invented (a value no source gave is null); the pinned files
under `docs/references/` are read-only; the wiki and `README.md` are updated in the same change as the code.
