-- C.A.S.M Phase 1 reference-data schema: the classification taxonomy (asset class, base product,
-- product code) and the master data tables. The seed migrations fill the ref_* tables from the
-- pinned files in docs/references/master-data.

-- Re-runnable: drop everything that depends on the tables below (the security data of migration 01,
-- then the reference tables with foreign keys), because DuckDB cannot replace a referenced table.
DROP VIEW IF EXISTS sec_v_listing;
DROP TABLE IF EXISTS sec_exception_queue;
DROP TABLE IF EXISTS sec_listing;
DROP TABLE IF EXISTS sec_instrument_swp_leg;
DROP TABLE IF EXISTS sec_instrument_swp_contract;
DROP TABLE IF EXISTS sec_instrument_fwd_contract;
DROP TABLE IF EXISTS sec_instrument_opt_series;
DROP TABLE IF EXISTS sec_instrument_fut_contract;
DROP TABLE IF EXISTS sec_instrument_fnd;
DROP TABLE IF EXISTS sec_instrument_fi_bond;
DROP TABLE IF EXISTS sec_instrument_eq_warrant_right;
DROP TABLE IF EXISTS sec_instrument_eq_spt;
DROP TABLE IF EXISTS sec_identifier_xref;
DROP TABLE IF EXISTS sec_instrument;
DROP TABLE IF EXISTS sec_issuer;
DROP TABLE IF EXISTS ref_venue;
DROP TABLE IF EXISTS ref_product_code;

-- Taxonomy: the spine (T1)
CREATE OR REPLACE TABLE ref_asset_class (
    code        CHAR(2) PRIMARY KEY,
    name        TEXT NOT NULL
);

CREATE OR REPLACE TABLE ref_base_product (
    code         CHAR(3) PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL
);

CREATE OR REPLACE TABLE ref_product_code (
    code              TEXT PRIMARY KEY,
    asset_class_code  CHAR(2) NOT NULL REFERENCES ref_asset_class (code),
    base_product      CHAR(3) NOT NULL REFERENCES ref_base_product (code),
    description       TEXT NOT NULL,
    source            TEXT NOT NULL CHECK (source IN ('CASM', 'ISDA', 'MX3')),
    subtype_table     TEXT NOT NULL CHECK (subtype_table IN (
        'sec_instrument_eq_spt', 'sec_instrument_eq_warrant_right', 'sec_instrument_fi_bond',
        'sec_instrument_fnd', 'sec_instrument_fut_contract', 'sec_instrument_opt_series',
        'sec_instrument_fwd_contract', 'sec_instrument_swp_contract')),
    desk_family       TEXT,      -- T7: null where the taxonomy does not define it
    cftc_asset_class  TEXT,      -- T4: regulatory attributes, null where not defined
    mifid_category    TEXT,
    isda_path         TEXT,
    CHECK (code LIKE asset_class_code || '-' || base_product || '-%')
);

-- ISO 3166-1 countries (iso-country-codes.csv)
CREATE OR REPLACE TABLE ref_country (
    alpha2       CHAR(2) PRIMARY KEY CHECK (regexp_matches(alpha2, '^[A-Z]{2}$')),
    name         TEXT NOT NULL
);

-- ISO 10383 MIC registry, staged in full (iso-10383-mic.csv); ref_venue promotes the rows we use
CREATE OR REPLACE TABLE ref_mic_registry (
    mic                   CHAR(4) PRIMARY KEY,
    operating_mic         CHAR(4) NOT NULL,
    oprt_sgmt             TEXT NOT NULL CHECK (oprt_sgmt IN ('OPRT', 'SGMT')),
    market_name           TEXT NOT NULL,
    lei                   TEXT,
    market_category_code  TEXT,
    country               TEXT,      -- registry value, includes 'ZZ' for the placeholder MICs
    status                TEXT NOT NULL
);

-- Venue (trading location), never part of a product code. A venue is an attribute of a listing
-- (sec_listing); OTC status is derived from venue_type, not stored.
CREATE OR REPLACE TABLE ref_venue (
    mic            CHAR(4) PRIMARY KEY REFERENCES ref_mic_registry (mic),
    operating_mic  CHAR(4) NOT NULL REFERENCES ref_mic_registry (mic),
    name           TEXT NOT NULL,
    country        CHAR(2) REFERENCES ref_country (alpha2),   -- null on the placeholder venues
    venue_type     TEXT NOT NULL CHECK (venue_type IN ('EXCHANGE', 'MTF', 'OTF', 'SI', 'OTC', 'NONE')),
    lei            TEXT CHECK (regexp_matches(lei, '^[A-Z0-9]{20}$'))
);

-- GICS classification, flat: one row per sub-industry (the level an issuer is classified at),
-- lowest level leftmost, with its industry, industry group and sector alongside. The parent codes
-- are the code prefixes. A structure only, not a company-to-sector mapping; the 2018 edition is
-- stale.
CREATE OR REPLACE TABLE ref_gics (
    sub_industry_code         TEXT PRIMARY KEY CHECK (regexp_matches(sub_industry_code, '^[0-9]{8}$')),
    sub_industry_name         TEXT NOT NULL,
    sub_industry_description  TEXT,
    industry_code             TEXT NOT NULL,
    industry_name             TEXT NOT NULL,
    industry_group_code       TEXT NOT NULL,
    industry_group_name       TEXT NOT NULL,
    sector_code               TEXT NOT NULL,
    sector_name               TEXT NOT NULL,
    CHECK (industry_code = left(sub_industry_code, 6)
       AND industry_group_code = left(sub_industry_code, 4)
       AND sector_code = left(sub_industry_code, 2))
);

-- ISDA Taxonomy v2.0, equity sheet ("Equity Full"): one row per base product, sub-product and
-- transaction type. The mapping from our product codes to these rows is not one-to-one, so
-- ref_product_code.isda_path stays null for now.
CREATE OR REPLACE TABLE ref_isda_equity_taxonomy (
    isda_row_no       INTEGER PRIMARY KEY,
    base_product      TEXT NOT NULL,
    sub_product       TEXT,
    transaction_type  TEXT
);
