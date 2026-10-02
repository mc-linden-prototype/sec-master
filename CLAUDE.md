---
name: claude-project-instructions
description: Project instructions for Claude Code: scope, repository layout, wiki rules, Python and database standards, data rules and testing.
---

# CLAUDE.md

## Project

C.A.S.M (Cross Asset Security Master) is a security master — **reference data only** (what
a security is, never what is owned: no positions, quantities, values or exposure). We are
building a **Phase 1 prototype** to demonstrate the core architectural tenets (T1–T7) on the
Linden Advisors 13F-HR filing, used purely as a sample list of instruments, plus the master data
under `docs/references/`. Scope, tenets, data model, rules, work plan and acceptance criteria:
`docs/wiki/1_3-project-scope.md`. Read the wiki in the order `README.md`
gives before starting work, and keep work inside Phase 1 scope (the 17 Tier 1 product codes).
Ideas beyond scope go in the Phase 2 roadmap, not in code.

Phase 1 is a **static, one-time load** that shows the model works, not an operational database.
Day-to-day operation (corporate actions, reference data changes, feeds) is described in
`docs/wiki/1_1-sec-master-ops-flow.md` and is not built.

In the classification page, Phase 1 items are bold and underlined (`<u>**…**</u>`) and Phase 2
reference items are plain.

## Repository layout

- `src/casm/` — the package (imported as `casm.*`); build config in root `pyproject.toml`
- `tests/` — mirrors `src/casm/` exactly
- `docs/references/` — baseline input data and its `source.txt` provenance files (listed with origins in `docs/wiki/2_0-data-sources.md`)
- `src/db/` — the generated DuckDB file `casm.db` (rebuilt by the CLI, not committed)
- `docs/wiki/` — the wiki
- `README.md` — root index into the wiki

## Architecture documentation (keep current, same change as the code)

Two layers, both mandatory:

1. **`README.md`** (repo root) — the front door and index: quick start, monorepo layout, skills, a table of
   wiki pages, and one line per subsystem under `src/casm/` linking to its wiki page. Detail lives in the wiki.
2. **`docs/wiki/`** — the wiki. Numbered markdown pages (`1_0-…`, `1_1-…`, `2_0-…`; the leading digit
   groups them: 1 overview and scope, 2 data and classification, 3 design). `README.md` refers to it; detail lives here, not in the index.

The wiki documents **what is**, not what will be. Do not create placeholder or "to be" pages or
sections; create a page only when the thing it describes exists in code or data, and write it
from the actual code. `1_1-sec-master-ops-flow.md` (the operating model; Phase 1 is a static
one-time load) and `1_3-project-scope.md` are the only forward-looking pages (the Phase 2+ section of `1_0-introduction.md` is a summary of them).

Update both in the same change whenever you:
- add, remove or rename a subsystem (a folder under `src/casm/`) or a dataset under `docs/references/` (also update `2_0-data-sources.md`)
- change a subsystem's responsibilities, public interface, data model/schema, or dependencies
- make or reverse a design decision, or discover a gap worth recording

Wiki page rules:
- Every markdown file starts with YAML front matter holding `name` and `description`.
- These are system docs (product documentation): no status, draft or last-updated lines, and no progress or "not yet done" messaging. Describe the design and its known gaps.
- A subsystem page covers: purpose, key files, inputs/outputs, dependencies and dependents, and
  known gaps. Describe what exists, not what is hoped for.
- Decisions and open questions go in the page they affect; Phase 2 ideas go in the roadmap (`1_3-project-scope.md` section 13) and the Phase 2+ part of `1_0-introduction.md`; keep the two consistent.
- Every page must appear in the `README.md` table; never leave an orphan page or a dead link.
- Do not describe the overall/full-scale design of the system. Document Phase 1 as built.

Before finishing any task that touched `src/casm/` or `docs/references/`, check whether the wiki and
`README.md` need updating, and say in your summary what you updated.

## Python standards

### Version target

Python `>=3.12,<3.15`. Prefer stdlib over third-party packages; use PEP 695 generics
(`class Foo[T]`) over `TypeVar`.

### Typing

- Annotate every variable and function/method parameter where a type can be given, and every
  return type.
- Built-in generics (`list[str]`, `dict[str, object]`); `X | None`, never `Optional[X]`.
- Call sites use keyword arguments; define parameters keyword-only (`def f(*, a: int, b: str)`)
  except for a single obvious argument. Bundle into a `pydantic.BaseModel` config object at
  four or more parameters.

### Models

- No `@dataclass`, and no classes for plain data with no behavior.
- Default to `pydantic.BaseModel` for typed records, reports and config.
- An explicit `class` for things with behavior, state or lifecycle (e.g. a repository).
- `abc.ABC` only for an interface with multiple real implementations; `Protocol` only for genuine
  structural typing. No base classes for plain data.

### Docstrings

Trivial functions get a one-liner or none. Non-trivial public functions, behavioral classes,
loaders and validators get Google-style `Args:`/`Returns:`/`Raises:`. Module docstrings are at most
2-3 sentences. No noise (restating parameter names, explaining obvious assignments).

### Error handling

Raise specific `Exception` subclasses for package failures, with actionable messages
(`raise ReferenceDataError("GICS workbook has no 'Sector' header row.")`, not `ValueError("bad")`).
Wrap low-level failures at package boundaries. Never silently drop bad input rows — route them
to the exception queue.

### Files and modules

- Keep modules focused; split by domain, no giant utils files.
- `__init__.py` files stay empty; import from the defining module directly.
- Each folder that needs constants gets its own `statics.py`, in the folder whose domain they
  belong to.
- No function-local imports; hoist to module top level.

## Database

- Main database is a DuckDB file, `src/db/casm.db` by default. The path is passed in from the CLI,
  never hard-coded in a module. It is accessed only through the `duckdb` Python API inside
  `db/`; no ORM.
- Write standard SQL; avoid DuckDB-only syntax where a portable form exists.
- The DuckDB Python API is synchronous, so database code is too. No async.
- Table names: `ref_` for reference data (taxonomy, master data), `sec_` for security data
  (issuers, instruments, identifiers, exceptions).
- Migrations are plain, versioned SQL files applied in name order. Schema and seed data are
  separate files, and seed data always comes last. Integrity lives in the database (foreign keys,
  `CHECK` and unique constraints), not only in Python; DuckDB has no triggers.
- Schema changes are reflected in the wiki's database page in the same change.
- Every integrity rule (R1–R10 in the plan) needs a positive test and a negative-insert test.

## Data rules

- `docs/references/` inputs are read-only and pinned by SHA-256; a build never re-fetches them.
- Reference data only: never compute, store or report position values, amounts or exposure. The
  pinned input file is the raw layer; there is no raw-holdings table.
- Every golden-record attribute keeps its source and as-of date; synthetic fixtures carry
  `is_synthetic = true`, live in a separate file, and are excluded from reconciliation.
- Entities and instruments stay separate: no issuer attributes on instrument tables.
- Classification and validation are table-driven and deterministic. Every baseline row ends as
  a golden instrument or an exception-queue entry with a reason code — never dropped or guessed.
- Do not hard-code file paths in modules; pass them in from the CLI/config.

## Testing

- Deterministic, no network. Tests use small fixtures or the real files under `docs/references/`.
- `pytest`; tests mirror `src/casm/` (`src/casm/securities/cusip.py` → `tests/securities/test_cusip.py`).
- Add tests with the code, not afterward.
- Prefer real collaborators (a real in-memory DuckDB database) over mocks.

## Tooling

Use `uv` for environments and commands.
- `uv run black .`
- `uv run ruff check --fix .`
- `uv run pytest`

## Anti-patterns

- Adding scope beyond Phase 1 instead of logging it in the backlog.
- Changing code without updating `README.md` and the wiki.
- Dropping or guessing data silently, or fabricating a record the source cannot support (e.g. an
  option series from a 13F put/call row).
- Building operational features in Phase 1 (status lifecycles, change handling, triggers).
- Base classes or interfaces for plain data objects.
- Function-local imports; barrel `__init__.py` files.
