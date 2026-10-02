---
name: data-sources
description: Every data source used by Phase 1, where it was sourced from, and which folder under docs/references/ holds it.
---

# Data Sources

> Index: [README.md](../../README.md) · Seed rules: [Project scope](1_3-project-scope.md) section 8.2

All inputs sit under `docs/references/`, are read-only and pinned by SHA-256 where a `source.txt` records
one. A build never re-fetches them. Each folder has its own `source.txt` with the origin.

## Baseline filing: `docs/references/linden-sec-filings/`

| Folder | File | Source |
|---|---|---|
| `holdings/` | `13F-HR-56990.xml` | SEC EDGAR, Linden Advisors Form 13F-HR information table: https://www.sec.gov/Archives/edgar/data/1279396/000119312526350767/0001193125-26-350767-index.htm |
| `asset-classes-coverage/` | `LINDEN-ADVISORS-2A-brochure-1020409.pdf` | SEC IAPD, Form ADV Part 2A brochure: https://files.adviserinfo.sec.gov/IAPD/Content/Common/crd_iapd_Brochure.aspx?BRCHR_VRSN_ID=1020409 |

The filing has 638 rows and is the raw layer; there is no holdings table. The brochure is evidence of which
asset classes the firm trades.

## Master data: `docs/references/master-data/`

| Folder | File(s) | Source |
|---|---|---|
| `gics-classification/` | `Effective+until+March+17+2023.xlsx` | MSCI GICS structure: https://www.msci.com/indexes/index-resources/gics |
| `iso-country-codes/` | `iso-country-codes.csv` | ISO 3166-1, ISO Online Browsing Platform: https://www.iso.org/obp/ui/#search |
| `market-identifier-codes/` | `ISO10383_MIC.xlsx` | ISO 10383 MIC registry via ISO 20022: https://www.iso20022.org/market-identifier-codes |
| `product-classification-isda/` | three ISDA taxonomy workbooks (`.xls`/`.xlsx`: OTC Derivatives v1.0 reporting, EQ-CR-FX-IR v2.0, Commodities v2.0) | ISDA Taxonomy v2.0: https://www.isda.org/tag/taxonomy-v2-0/ |

## Security data: `docs/references/security-data/`

Retrieved 2026-09-30.

| Folder | File(s) | Source |
|---|---|---|
| (root) | `sample-selection.csv` | Derived from the 13F: the 100 highest-`value` rows in each class `RT`, `COM`, `SDBCV` plus the one `ADR` row = 301 rows. `value` picks the sample and is not stored. |
| `openfigi/` | `openfigi-mapping-by-cusip.json`, `openfigi-mapping-by-ticker-underlying.json` | OpenFIGI mapping API, https://api.openfigi.com/v3/mapping (no key). Raw responses: one job per sampled CUSIP (301; 13 not found) and one per underlying ticker. |
| `nasdaq-trader/` | `nasdaqlisted.txt`, `otherlisted.txt` | Nasdaq Trader symbol directory, https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt and `otherlisted.txt`. Test issues ignored. |
| `sec/` | `company_tickers_exchange.json` | SEC ticker file, https://www.sec.gov/files/company_tickers_exchange.json |
| `sec/` | `edgar-submissions-trimmed.json` | EDGAR submissions API, https://data.sec.gov/submissions/CIK##########.json, 214 CIKs, trimmed to cik, entityType, sic, sicDescription, name, tickers, exchanges, lei, state of incorporation and former names. |

## How the data reaches the database

The sources feed `src/casm/db/migrations/` (reference data seed `02_seed_ref_data.sql`, venues
`03_seed_venues.sql`, security seed `04_seed_security_data.sql`). What each datapoint is taken from is in the
table in [Project scope](1_3-project-scope.md) section 8.2.

## Not used or not obtained

No paid vendor feed (Bloomberg Terminal, MSCI, Refinitiv, Morningstar) was used. GICS per issuer, SEDOL, ISIN
and LEI are not available from free sources, so they are null or absent; the EDGAR SIC code stands in for GICS.
