# C.A.S.M Security Master

C.A.S.M (Cross Asset Security Master) is a **security master**: reference data only, meaning what a
security *is*, never what is owned. This Phase 1 prototype shows that a taxonomy, separate issuers and
instruments, database-enforced relationships and one identifier model work, on a sample of 301 instruments
from a Linden Advisors 13F-HR filing. Detail lives in the wiki at [`docs/wiki/`](docs/wiki/).
The wiki describes what exists today, not what is planned, except the operations flow and project scope pages.

## Quick start

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

| What | Address |
|---|---|
| Web UI (Securities, Reference Data, Wiki) | http://127.0.0.1:9095 |
| API Swagger docs | http://127.0.0.1:9099/docs |

Ports, flags, troubleshooting and the tech stack: [Tech stack](docs/wiki/3_2-tech-stack.md) and the
`launch-app` skill below.

## Monorepo layout

One repository holds the database, the API, the UI, the documentation, the pinned input data and the tests.

| Path | What lives there |
|---|---|
| `src/main.py` | Entry point: rebuilds the database, starts the API (9099) then the UI (9095); `--check` preflight |
| `src/casm/db/` | SQL migrations (`00` to `04`) and `migrate.py`, which deletes and rebuilds `casm.db` |
| `src/casm/api/` | FastAPI app, request logging, shared `utils/`, versioned routes in `v1/` (securities, reference, wiki) |
| `src/casm/ui/` | The static web UI and the small server that serves it |
| `src/casm/preflight.py` | Environment check behind `--check` |
| `tests/` | Mirrors `src/casm/`; real DuckDB, no mocks, no network |
| `docs/wiki/` | The wiki (numbered pages) |
| `docs/references/` | Pinned, read-only input data with `source.txt` provenance |
| `docs/validation/` | The UI validation report and screenshots |
| `.prototype/` | The design prototype the UI follows |
| `.claude/skills/` | Claude skills for this repository |

## Claude skills

Skills in [`.claude/skills/`](.claude/skills/) that Claude Code can run for anyone working in the repo:

| Skill | Use it to |
|---|---|
| [`launch-app`](.claude/skills/launch-app/SKILL.md) | Set up the virtual environment, confirm the machine is ready, run the app, fix setup problems |
| [`explain-casm`](.claude/skills/explain-casm/SKILL.md) | Learn what the system is for, how the repo is organised and where to find things |
| [`validate-ui`](.claude/skills/validate-ui/SKILL.md) | Launch the app, drive it in Chrome over the DevTools Protocol and verify the data on every screen; writes [`docs/validation/ui-validation-report.md`](docs/validation/ui-validation-report.md) |

## Read the wiki first, in this order

Read the wiki before changing code or data. The order goes from why, to what, to how. The UI's **Wiki** tab
shows the same pages in file order, with the diagrams drawn. Every wiki page and this file starts with
`name` and `description` front matter.

| Page | Topic |
|------|-------|
| [Introduction](docs/wiki/1_0-introduction.md) | What C.A.S.M aims to achieve; Phase 1 (prototype) and Phase 2+ (further build-out) at a high level |
| [Operations flow](docs/wiki/1_1-sec-master-ops-flow.md) | How a security master operates day to day, which parts Phase 1 builds, and the surrounding vendor, market data and pricing systems (forward-looking) |
| [Project scope](docs/wiki/1_3-project-scope.md) | Prototype plan: tenets, scope, data model, rules, work plan, acceptance criteria, seed data sources (forward-looking) |
| [Data sources](docs/wiki/2_0-data-sources.md) | Every source, where it came from, and which `docs/references/` folder holds it |
| [Asset classification](docs/wiki/2_1-asset-classification.md) | Design principles, code format, asset classes, base products and instruments (Phase 1 = bold and underlined) |
| [Taxonomy](docs/wiki/2_2-taxonomy.md) | Phase 1 hierarchy (EQ, FI), decision trees and regulatory alignment for the 17 product codes |
| [Database schema](docs/wiki/3_1-database-schema.md) | Schema, integrity rules and how the database enforces them, why normalized tables |
| [Tech stack](docs/wiki/3_2-tech-stack.md) | Stack, monorepo, ports, clean-machine setup, commands |
| [API and UI](docs/wiki/3_3-api-ui.md) | The `/api/v1` API (securities, reference, wiki), its layering, the web UI and its tests |

## What a security master solves

1. **Product classification.** Every instrument gets one product code from one taxonomy, so a
   convertible, a warrant or a swap is classified the same way wherever it appears.
2. **One view of firm-wide holdings.** One instrument and issuer identity across desks and
   systems lets exposure aggregate by issuer, underlying and asset class. The master supplies the
   keys; positions live elsewhere.
3. **One language across teams.** Investment, operations, risk and reporting work from the same
   firm-wide taxonomy, so a break is a data problem and not a naming dispute.
4. **Streamlined regulatory reporting.** Classifications follow industry standards (ISDA, CFTC,
   MiFID II / EMIR), and the regulatory attributes sit on the product code, so scope questions are
   answered from data. Detail: [Operations flow](docs/wiki/1_1-sec-master-ops-flow.md).

## Key decision: normalized tables, not a key-value store

Industry security masters use either a key-value (EAV) store of attributes, which is flexible and
carries per-attribute history but cannot enforce types or relationships, or normalized tables,
which are less flexible but let the database enforce integrity. C.A.S.M uses normalized tables
(a supertype `sec_instrument` plus per-family subtype tables) because the prototype's purpose is to
show integrity enforced by foreign keys and constraints. Detail and trade-offs:
[Database schema](docs/wiki/3_1-database-schema.md).

## Subsystems (as built)

- `src/casm/db/` — SQL migrations and the ad hoc runner `migrate.py` for the DuckDB file `src/casm/db/casm.db` (reference-data schema, security-data schema including venues and listings, taxonomy, GICS, ISO country, ISDA equity taxonomy and ISO 10383 MIC seed data, and the 301-row Linden security sample); tests in `tests/db/`; see [Database schema](docs/wiki/3_1-database-schema.md).
- `src/casm/api/` — the async FastAPI app on port 9099: rebuilds the database on launch, serves the versioned `/api/v1` routes (securities and issuers, reference, wiki), unpaged, in endpoints, service and queries layers, logging to the console and `logs/casm-api.log` with a request id on every line; tests in `tests/api/`; see [API and UI](docs/wiki/3_3-api-ui.md).
- `src/casm/ui/` — the web UI on port 9095 (Securities, Reference Data, Wiki) and the server that hosts it; tests in `tests/ui/`; see [API and UI](docs/wiki/3_3-api-ui.md).
- `src/casm/preflight.py` and `src/main.py` — the entry point and the `--check` environment verification; see [Tech stack](docs/wiki/3_2-tech-stack.md).

## Security seed data: universe and sources

The prototype's security data is a **sample of 301 of the 638 rows** of the Linden Advisors Form
13F-HR (accession 0001193125-26-350767): the 100 highest-`value` rows in each title of class `RT`,
`COM` and `SDBCV`, plus the single `ADR` row (`value` selects the sample and is not stored). Result:
213 issuers, 398 instruments (279 from the sample, 119 added as underlyings), 398 listings and 22
queued rows with a reason code. Every source, URL and folder: [Data sources](docs/wiki/2_0-data-sources.md); rules: [Project scope](docs/wiki/1_3-project-scope.md) section 8.2.

| Datapoint | Authoritative source |
|---|---|
| Universe, filing name, CUSIP, class | SEC EDGAR Form 13F-HR information table |
| Product code, share-class and composite FIGI, Bloomberg ticker | OpenFIGI (Bloomberg's open symbology service) |
| Exchange symbol, listing venue, round lot | Nasdaq Trader symbol directory |
| Issuer CIK, ticker to issuer link | SEC `company_tickers_exchange.json` |
| Issuer legal name, SIC, country of incorporation | SEC EDGAR submissions API |
| Country and venue master data | ISO 3166-1 and ISO 10383 |

No Bloomberg Terminal, MSCI, Refinitiv/Reuters, Morningstar or other paid feed was used. GICS,
SEDOL, ISIN and LEI were not obtainable from free authoritative sources and are null or absent.

## Known gaps (system-wide)

Product gaps between Phase 1 and a full security master, and what is still unknown. Detail sits in
the pages linked.

### Not in Phase 1 (Phase 2 and beyond)

- **Coverage.** Only equity and convertible bonds (17 product codes). The 13 Tier 3 equity codes, other asset classes (credit, rates, FX, commodity, funds, digital assets) and other bond types are out. [Asset classification](docs/wiki/2_1-asset-classification.md), [Project scope](docs/wiki/1_3-project-scope.md) section 4.
- **Change over time.** A static one-time load: no corporate actions, no history of identifiers, names, listings or attributes, no delisting or lifecycle status. [Operations flow](docs/wiki/1_1-sec-master-ops-flow.md) section 5.
- **Multiple sources.** One filing, and only 301 of its 638 rows, is the sample. No vendor feeds, source precedence, survivorship or per-attribute provenance; there is no cross-vendor golden record. [Project scope](docs/wiki/1_3-project-scope.md) section 13.
- **Identifiers and classification depth.** GICS is the stale 2018 structure with no company-level mapping (licensed data), and no SEDOL, ISIN or LEI is held (not obtainable from free authoritative sources); CFI, UPI and EMIR/SFTR flags are not held; `isda_path` and `desk_family` are empty. [Taxonomy](docs/wiki/2_2-taxonomy.md) section 4.
- **Instrument terms.** Bond coupon and maturity come from the filing name for 91 of 94 convertibles; no conversion ratio, currency or warrant terms are held, and no unit components. [Database schema](docs/wiki/3_1-database-schema.md) section 4.
- **Venue.** Listings exist only for the 301-row sample, with no per-venue FIGI. No trading calendars or sessions, digital-asset venues, cross-listing reconciliation beyond FIGI, venue fee, lot or tick history, or listing status. [Database schema](docs/wiki/3_1-database-schema.md) section 4.
- **Operating model.** The API is a read-only prototype: no writes, authentication, entitlements, data contracts or change events, no data-quality framework or exception workflow, no hosted database. [Operations flow](docs/wiki/1_1-sec-master-ops-flow.md), [API and UI](docs/wiki/3_3-api-ui.md).

### Unknowns and open decisions

- **Issuer of an index or a derivative.** Every instrument needs an issuer (R2), but an index or an OTC contract has none in the usual sense. [Asset classification](docs/wiki/2_1-asset-classification.md) section 6.1.
- **Underlying of convertibles, rights and warrants.** The filing does not contain their underlying common stock. The seed adds the issuer's listed common stock or ADS from OpenFIGI and the SEC ticker file. [Project scope](docs/wiki/1_3-project-scope.md) section 15.
- **Unobserved product codes.** The 13F has no options, futures, swaps, CFDs or forwards, so those codes have no instruments. [Project scope](docs/wiki/1_3-project-scope.md) sections 4.3 and 6.
- **Venue coverage.** What share of all 638 CUSIPs would resolve to a venue from free sources, and within API limits, is unknown; the 301-row sample resolved 279. [Project scope](docs/wiki/1_3-project-scope.md) section 8.2.
- **Mapping to ISDA.** Product codes do not map one-to-one onto ISDA taxonomy rows; a mapping rule is not defined. [Database schema](docs/wiki/3_1-database-schema.md) section 4.
- **Normalized tables at scale.** Whether a multi-vendor master needs a key-value layer for sparse, changing attributes is untested. [Database schema](docs/wiki/3_1-database-schema.md) section 1.
- **Unconfirmed assumptions.** The tenets await the architecture owner's confirmation, and the Tier 1 list is revised after the baseline is profiled. [Project scope](docs/wiki/1_3-project-scope.md) section 15.
