---
name: database-design
description: Phase 1 database schema: migrations, tables, how each integrity rule is enforced, and why normalized tables were chosen over a key-value store.
---

# Database Design (Phase 1 schema)

> Index: [README.md](../../README.md) · Plan: [Project scope](1_3-project-scope.md) · Taxonomy: [Taxonomy](2_2-taxonomy.md)

A deliberately small schema that shows the architecture. Reference data only: no positions, amounts, notionals or
values. Migrations in `src/casm/db/migrations/`, applied in name order; schema (DDL) and seed data (DML) are
separate files, seed last.

| File | Content |
|---|---|
| `00_ref_data_schema.sql` | Taxonomy (asset class, base product, product code) and master data tables |
| `01_security_data_schema.sql` | Issuers, instruments, identifiers, subtype tables, exception queue |
| `02_products_taxonomy.sql` | Seed: 2 asset classes, 9 base products, 17 product codes |
| `02_seed_ref_data.sql` | Seed: GICS flat (158 sub-industry rows with industry, group and sector), 249 ISO 3166-1 countries, 34 ISDA v2.0 "Equity Full" rows |
| `03_seed_venues.sql` | Seed: the ISO 10383 registry (2,883 MICs) into `ref_mic_registry`, then 13 venues into `ref_venue` (after `02`: venues reference `ref_country`) |
| `04_seed_security_data.sql` | Seed: 213 issuers, 398 instruments, identifiers, subtype rows, listings and 22 exception-queue rows from the 301-row sample ([Project scope](1_3-project-scope.md) section 8.2). Explicit ids, then sequences advanced past them |

**Applying them.** `uv run python src/casm/db/migrate.py [--db PATH]` (default `src/casm/db/casm.db`, not
committed) deletes the DuckDB file and its write-ahead log, runs every migration on a new database and prints
table counts, so a rebuild never depends on earlier state. The files are also re-runnable on an open connection
(the tests do this): schema files use `CREATE OR REPLACE` after dropping dependents in reverse order (`00` also
drops the `sec_*` tables), and each seed file starts with `DELETE FROM` for its tables and their dependents,
children first. Running a seed file alone empties its dependents, so run the later seed files again.

## 1. Why normalized tables, not a key-value store

| | Key-value (EAV) store | Normalized tables (chosen) |
|---|---|---|
| Shape | `(security_id, attribute_name, value, source, as_of)` | Supertype `sec_instrument` plus a subtype table per product family |
| Adding an attribute | A new row value | A migration |
| Provenance and history | Natural: every row carries source and date | Needs row-level or side-table provenance |
| Types and constraints | Text or variant; not checkable | Real types, `NOT NULL`, `CHECK`, foreign keys |
| Relationships | A value that holds another id; no foreign key | True foreign keys |
| Querying | Pivots and self-joins | Plain joins and indexes |
| Vendor onboarding | Easy | Slower |

Key-value suits a multi-vendor golden-source master with many sparse, changing attributes. This prototype shows
that **the database enforces integrity** (T1, T2, T3, T6): a key-value model cannot express "a convertible must
reference an equity underlying" or "an option needs a strike" as a constraint. The data is small and well known
(17 codes), so the flexibility is not worth it. The one hybrid is a `JSON` `terms` column on warrants and rights
for terms that exist only as prospectus text. Per-attribute history and survivorship are Phase 2
([Project scope](1_3-project-scope.md) section 13). Prefixes: `ref_` reference data, `sec_` security data.

## 2. Tables

| Group | Tables | Purpose |
|---|---|---|
| Taxonomy (`00`) | `ref_asset_class`, `ref_base_product`, `ref_product_code` | The spine (T1), one table per code level. The product-code row names the subtype table, and carries regulatory and desk attributes (null where the taxonomy defines none) |
| Master data (`00`) | `ref_country`, `ref_gics` (flat: one row per sub-industry, lowest level leftmost, with its industry, industry group and sector), `ref_isda_equity_taxonomy` | Loaded from the pinned files under `docs/references/master-data/` |
| Venue (`00`, `01`) | `ref_mic_registry`, `ref_venue`, `sec_listing`, view `sec_v_listing` | The registry is staged in full; `ref_venue` holds the venues used (US equity exchanges `XNYS XNAS XASE ARCX`, other US equity venues `BATS EDGX IEXG`, US listed derivatives `XCBO XCME XCBT IFUS`, placeholders `XXXX` unlisted and `XOFF` off-exchange). `sec_listing` is one row per instrument per venue (`UNIQUE (instrument_id, mic)`) holding the venue symbol, FIGI, composite FIGI, RIC, Bloomberg ticker, currency, lot and tick size, settlement cycle, `primary_marker`, and `source`, `as_of`, `confidence`. The view adds `is_primary` and the derived `is_otc` |
| Entity (`01`) | `sec_issuer` | Legal entity: name, type, country (FK `ref_country`), CUSIP issuer prefix (`cusip6`, the issuer key for the filing, which has no CIK), CIK, LEI, SIC, optional GICS code (FK to `ref_gics.sub_industry_code`, so sub-industry level only; instruments inherit it through the issuer) (T2) |
| Core (`01`) | `sec_instrument`, `sec_identifier_xref` | One row per instrument with one product code and an `issuer_id`; one identifier table for all codes (T5) |
| Subtypes (`01`) | `sec_instrument_eq_spt`, `sec_instrument_eq_warrant_right`, `sec_instrument_fi_bond`, `sec_instrument_fnd`, `sec_instrument_fut_contract`, `sec_instrument_opt_series`, `sec_instrument_fwd_contract`, `sec_instrument_swp_contract`, `sec_instrument_swp_leg` | Product terms; see the map below |
| Exceptions (`01`) | `sec_exception_queue` | Rows that cannot become an instrument, identified by file hash and row number, with a reason code (`UNMAPPED_CLASS`, `AMBIGUOUS_CLASS`, `OPT_SERIES_UNRESOLVED`, `UNDERLYING_UNRESOLVED`, `INVALID_IDENTIFIER`, `ISSUER_UNRESOLVED`, `VENUE_UNRESOLVED`). No raw-holdings table: the pinned file is the raw layer, and no amounts or values are stored |

Product code to subtype table:

| Table | Product codes |
|---|---|
| `sec_instrument_eq_spt` | `EQ-SPT-COMMON`, `-PREF`, `-DEP-RCPT`, `-INDEX` |
| `sec_instrument_eq_warrant_right` | `EQ-SPT-WARRANT`, `-RIGHTS`, `-UNIT` |
| `sec_instrument_fi_bond` | `FI-BND-CONV` |
| `sec_instrument_fnd` | `EQ-FND-ETF`, `-ETP` |
| `sec_instrument_fut_contract` | `EQ-FUT-INDEX`, `-SINGLE` |
| `sec_instrument_opt_series` | `EQ-OPT-VANILLA` |
| `sec_instrument_fwd_contract` | `EQ-FWD-PRICE-RTN`, `EQ-CFD-PRICE-RTN` |
| `sec_instrument_swp_contract` (+ `_leg`) | `EQ-SWP-PRICE-RTN`, `EQ-PSW-PRICE-RTN` |

## 3. How the integrity rules are enforced

Each subtype row carries `product_code`, tied to `sec_instrument` by a composite foreign key
`(instrument_id, product_code)` and limited by a `CHECK` to its own codes. An underlying is the
same pair, limited to the codes allowed as an underlying. This is a static one-time load, so
the schema uses only foreign keys, `CHECK`s and unique constraints: no triggers, and no lifecycle or
workflow columns (instrument status, identifier validity, exception status).

| Rule | Mechanism |
|---|---|
| R1 instrument has exactly one matching subtype row | The composite FK and per-table `CHECK` stop a subtype row attaching to the wrong code and keep subtype tables disjoint. That every instrument *has* a row in the table the taxonomy names is a load-time check (a query run after the load and in tests) |
| R2 issuer by key | `sec_instrument.issuer_id NOT NULL` foreign key; no issuer columns on instrument tables |
| R3 convertible underlying is equity spot | Composite FK plus `CHECK` on `underlying_product_code` |
| R4 warrant or right has an equity underlying | Same; units have none (`CHECK`). Same-issuer warning is not in the database |
| R5 option needs strike, expiry, style | `NOT NULL` and `CHECK` on `sec_instrument_opt_series` |
| R6 identifier resolves to one instrument | `UNIQUE (scheme, value)` |
| R7 swap has return and funding legs | Load-time check: each swap contract has a `RETURN` and a `FUNDING` leg |
| R8 depositary receipt underlying flagged | `CHECK` (issuer id or `underlying_unresolved`) |
| R9 no option series without strike or expiry | Same `NOT NULL`; the loader records `OPT_SERIES_UNRESOLVED` in `sec_exception_queue` |
| R10 source and as-of | `NOT NULL source, as_of` on issuer, instrument, identifier and every subtype contract row. `sec_instrument_swp_leg` carries neither: a leg inherits them from its swap contract row |
| R11 every instrument has at least one listing | Load-time check, like R1: a query for instruments with no `sec_listing` row. Unlisted and OTC instruments get a placeholder listing, so no `venue` is ever null |
| R12 at most one primary listing per instrument | `UNIQUE (instrument_id, primary_marker)`. DuckDB has no partial unique index, so the flag is stored as `primary_marker` (`1` or null, nulls are distinct) and the view derives `is_primary` |
| R13 venue is a registry MIC; placeholders are defaults | `ref_venue.mic` is a foreign key to `ref_mic_registry`; `sec_listing.mic` to `ref_venue`; `CHECK`s make `XXXX`/`XOFF` listings, and only those, `source = 'DEFAULT'` with `confidence = 'LOW'` |

## 4. Decisions and known gaps

- **Forwards and CFDs share `sec_instrument_fwd_contract`:** both are OTC price-return contracts on one underlying.
  Confirm or split.
- **Portfolio swaps have no underlying and no holdings** (a basket would be position data): contract header and
  legs only.
- **Provenance is per row**, not per attribute (R10 at its simplest).
- **Security seed decisions.**
  - An issuer is one row per CIK (SEC ticker file); a company with two CUSIP prefixes (a SPAC and its successor)
    has one `sec_issuer` row, `cusip6` holds the common stock's prefix, and the other prefix stays on the full
    CUSIP in `sec_identifier_xref`.
  - `issuer_type` is `SPAC` when the EDGAR SIC code is 6770, else `OPERATING_COMPANY`; `country_code` is null for
    the 20 issuers whose EDGAR incorporation field is empty.
  - The filing has no underlying for convertibles, warrants or rights (R3, R4), so the issuer's common stock or ADS
    is added as a separate instrument (source `OPENFIGI`, no CUSIP): 119 of them. A convertible into an ADS
    references `EQ-SPT-DEP-RCPT`. The ADR row has `underlying_unresolved` true (R8).
  - `is_144a` is true only when the name says `144A`, else null. Warrant terms and expiry, bond conversion ratio and
    currency are null: no source gave them. The seed generator is a one-off script; only its pinned inputs and
    output are in the repository.
- **Venue belongs to a listing, never the product code.** OTC is derived from `venue_type` (`OTC`, `NONE`) in
  `sec_v_listing`, never stored. A clearing house is not a venue.
- **Ticker lives on the listing**, not in `sec_identifier_xref` (it differs per venue and is not unique). The xref
  keeps CUSIP, ISIN and share-class FIGI; `sec_listing` holds per-venue FIGI, composite FIGI, symbol, RIC and
  Bloomberg ticker.
- **Venue design choices.** `ref_venue` is keyed by `mic` (like `ref_country`) with no `timezone`, `is_active`,
  `attributes` or timestamps; `sec_listing` drops `status`, `attributes` and timestamps and names the date `as_of`.
  `venue_type` is set in the seed because the registry's market category does not give it. `XXXX` and `XOFF` have
  registry country `ZZ`, so their `ref_venue.country` is null. `source` also allows `EXCHANGE_SPEC`.
- **Venue data covers the sample only:** 398 listings (249 `XNAS`, 52 `XNYS`, 3 `XASE`, 94 bond placeholders:
  `XOFF` 76, `XXXX` 18), from Nasdaq Trader and OpenFIGI. The per-venue `figi` is empty (OpenFIGI gives Bloomberg
  exchange codes, not MICs). Confidence: `HIGH` (two sources agree), `MEDIUM` (one), `LOW` (default or name-parsed).
  Left out: trading calendars and sessions, digital-asset venues, cross-listing reconciliation beyond FIGI, venue
  fee, lot and tick history, corporate actions that change venue or status.
- **Master data:** `ref_gics` (2018 structure, stale since 2023-03-17) and `ref_country`
  (`iso-country-codes.csv`: 249 rows, name and alpha-2 only, names verbatim from the source, so
  `Western Sahara*` keeps its ISO footnote asterisk) are seeded by `02_seed_ref_data.sql`.
  `ref_isda_equity_taxonomy` (ISDA v2.0 workbook, "Equity Full" sheet only) is seeded with its 34
  rows too; the sheet's `Industry Sector` column is an unfilled placeholder and is not loaded. `ref_product_code.isda_path` stays null because product codes do not map
  one-to-one onto ISDA rows (for example `EQ-OPT-VANILLA` spans single name, index and basket).
- **Master data left out:** the ISDA credit, FX, interest-rate and commodity sheets and the
  ISDA v1.0 files, because Phase 1 is equity and fixed-income convertibles only.
- **Not built:** a title-of-class map, unit components, and the issuer convention for
  `EQ-SPT-INDEX` and derivatives (an open question in
  [Asset classification](2_1-asset-classification.md) section 6.1).
- **Engine:** DuckDB, one file at `src/casm/db/casm.db` (deleted and rebuilt by `migrate.py`, not committed). Sequences
  stand in for identity columns, `regexp_matches` for `~`, and `JSON` for `JSONB`. DuckDB has no
  triggers and no `ON DELETE` actions, which is why R1 and R7 are load-time checks.
