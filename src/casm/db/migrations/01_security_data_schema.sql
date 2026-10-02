-- C.A.S.M Phase 1 products schema: issuers, instruments, identifiers, subtype tables and
-- the exception queue. Reference data only (no positions, amounts, values). Needs 00 applied first.
-- Static one-time load: no lifecycle or workflow columns, and no triggers.

-- Re-runnable: drop in reverse dependency order, because DuckDB cannot replace a referenced table.
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

-- Issuers (entities) are separate from instruments (T2)
CREATE OR REPLACE SEQUENCE seq_sec_issuer;
CREATE OR REPLACE TABLE sec_issuer (
    issuer_id      BIGINT PRIMARY KEY DEFAULT nextval('seq_sec_issuer'),
    legal_name     TEXT NOT NULL,
    issuer_type    TEXT NOT NULL CHECK (issuer_type IN
        ('OPERATING_COMPANY', 'SPAC', 'FUND_SPONSOR', 'OTHER')),
    country_code   CHAR(2) REFERENCES ref_country (alpha2),
    cusip6         TEXT UNIQUE CHECK (regexp_matches(cusip6, '^[0-9A-Z*@#]{6}$')),   -- CUSIP issuer prefix
    cik            TEXT UNIQUE CHECK (regexp_matches(cik, '^[0-9]{10}$')),
    lei            TEXT UNIQUE CHECK (regexp_matches(lei, '^[A-Z0-9]{20}$')),
    sic            TEXT,
    gics_code      TEXT REFERENCES ref_gics (sub_industry_code),   -- issuer-level; null in the prototype
    source         TEXT NOT NULL,
    as_of          DATE NOT NULL,
    is_synthetic   BOOLEAN NOT NULL DEFAULT FALSE
);

-- Instrument supertype: one row per instrument, one product code, issuer by FK only (R2)
CREATE OR REPLACE SEQUENCE seq_sec_instrument;
CREATE OR REPLACE TABLE sec_instrument (
    instrument_id  BIGINT PRIMARY KEY DEFAULT nextval('seq_sec_instrument'),
    product_code   TEXT NOT NULL REFERENCES ref_product_code (code),
    issuer_id      BIGINT NOT NULL REFERENCES sec_issuer (issuer_id),
    security_name  TEXT NOT NULL,
    source         TEXT NOT NULL,
    as_of          DATE NOT NULL,
    is_synthetic   BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (instrument_id, product_code)   -- target of the subtype and underlying FKs
);

-- One identifier model for every product code (T5); a (scheme, value) is unique (R6)
CREATE OR REPLACE SEQUENCE seq_sec_identifier_xref;
CREATE OR REPLACE TABLE sec_identifier_xref (
    xref_id        BIGINT PRIMARY KEY DEFAULT nextval('seq_sec_identifier_xref'),
    instrument_id  BIGINT NOT NULL REFERENCES sec_instrument (instrument_id),
    scheme         TEXT NOT NULL CHECK (scheme IN ('CUSIP', 'ISIN', 'FIGI')),   -- ticker is per venue: sec_listing
    value          TEXT NOT NULL,
    source         TEXT NOT NULL,
    as_of          DATE NOT NULL,
    UNIQUE (scheme, value),
    CHECK (CASE scheme
        WHEN 'CUSIP' THEN regexp_matches(value, '^[0-9A-Z*@#]{9}$')
        WHEN 'ISIN'  THEN regexp_matches(value, '^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
        WHEN 'FIGI'  THEN regexp_matches(value, '^BBG[A-Z0-9]{9}$')
        ELSE FALSE END)
);

-- One row per instrument per venue (rule 2); every instrument has at least one (R11, load-time
-- check). Unlisted or OTC instruments use the placeholder venues XXXX and XOFF. Venue-specific
-- identifiers sit here, not on sec_identifier_xref: FIGI there is the share-class level.
CREATE OR REPLACE SEQUENCE seq_sec_listing;
CREATE OR REPLACE TABLE sec_listing (
    listing_id        BIGINT PRIMARY KEY DEFAULT nextval('seq_sec_listing'),
    instrument_id     BIGINT NOT NULL REFERENCES sec_instrument (instrument_id),
    mic               CHAR(4) NOT NULL REFERENCES ref_venue (mic),
    symbol            TEXT,
    figi              CHAR(12) UNIQUE CHECK (regexp_matches(figi, '^BBG[A-Z0-9]{9}$')),   -- per-venue FIGI
    composite_figi    CHAR(12) CHECK (regexp_matches(composite_figi, '^BBG[A-Z0-9]{9}$')),
    ric               TEXT,
    bbg_ticker        TEXT,
    currency          CHAR(3),
    lot_size          NUMERIC CHECK (lot_size > 0),
    tick_size         NUMERIC CHECK (tick_size > 0),
    settlement_cycle  TEXT CHECK (regexp_matches(settlement_cycle, '^T\\+[0-9]$')),
    primary_marker    SMALLINT CHECK (primary_marker = 1),   -- 1 on the home-market listing, else null
    source            TEXT NOT NULL CHECK (source IN
        ('OPENFIGI', 'NASDAQ_TRADER', 'SEC', 'EXCHANGE_SPEC', 'MANUAL', 'DEFAULT')),
    as_of             DATE NOT NULL,
    confidence        TEXT NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    is_synthetic      BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (instrument_id, mic),
    UNIQUE (instrument_id, primary_marker),   -- R12: at most one primary listing (DuckDB has no partial unique index; nulls are distinct)
    CHECK ((mic IN ('XXXX', 'XOFF')) = (source = 'DEFAULT')),   -- R13: placeholders are defaults
    CHECK (mic NOT IN ('XXXX', 'XOFF') OR confidence = 'LOW')
);

-- OTC is derived from the venue, never stored (rule 4)
CREATE OR REPLACE VIEW sec_v_listing AS
SELECT l.*, (l.primary_marker IS NOT NULL) AS is_primary,
       v.venue_type, (v.venue_type IN ('OTC', 'NONE')) AS is_otc
FROM sec_listing l
JOIN ref_venue v USING (mic);

-- Subtype tables. Each carries the instrument's product_code, tied to the instrument row by a
-- composite FK and restricted by CHECK, so a subtype row cannot attach to the wrong product code.
-- An "underlying" is likewise (id, product_code), restricted to the allowed underlying codes.

CREATE OR REPLACE TABLE sec_instrument_eq_spt (
    instrument_id           BIGINT PRIMARY KEY,
    product_code            TEXT NOT NULL CHECK (product_code IN
        ('EQ-SPT-COMMON', 'EQ-SPT-PREF', 'EQ-SPT-DEP-RCPT', 'EQ-SPT-INDEX')),
    share_class             TEXT,
    currency                CHAR(3),
    underlying_issuer_id    BIGINT REFERENCES sec_issuer (issuer_id),   -- depositary receipts
    underlying_unresolved   BOOLEAN NOT NULL DEFAULT FALSE,
    source                  TEXT NOT NULL,
    as_of                   DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    CHECK (product_code <> 'EQ-SPT-DEP-RCPT'
           OR underlying_issuer_id IS NOT NULL OR underlying_unresolved)          -- R8
);

CREATE OR REPLACE TABLE sec_instrument_eq_warrant_right (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code IN
        ('EQ-SPT-WARRANT', 'EQ-SPT-RIGHTS', 'EQ-SPT-UNIT')),
    underlying_instrument_id BIGINT,
    underlying_product_code  TEXT CHECK (underlying_product_code IN
        ('EQ-SPT-COMMON', 'EQ-SPT-PREF', 'EQ-SPT-DEP-RCPT')),
    exercise_price           NUMERIC CHECK (exercise_price > 0),
    exercise_ratio           NUMERIC CHECK (exercise_ratio > 0),
    expiry_date              DATE,
    terms                    JSON,    -- terms that exist only as prospectus text
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    FOREIGN KEY (underlying_instrument_id, underlying_product_code)
        REFERENCES sec_instrument (instrument_id, product_code),
    CHECK ((underlying_instrument_id IS NULL) = (underlying_product_code IS NULL)),
    CHECK ((product_code = 'EQ-SPT-UNIT') = (underlying_instrument_id IS NULL))   -- R4
);

CREATE OR REPLACE TABLE sec_instrument_fi_bond (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code = 'FI-BND-CONV'),
    underlying_instrument_id BIGINT NOT NULL,
    underlying_product_code  TEXT NOT NULL CHECK (underlying_product_code IN
        ('EQ-SPT-COMMON', 'EQ-SPT-DEP-RCPT')),                                    -- R3
    currency                 CHAR(3),
    coupon_rate              NUMERIC CHECK (coupon_rate >= 0),
    maturity_date            DATE,
    conversion_ratio         NUMERIC CHECK (conversion_ratio > 0),
    is_144a                  BOOLEAN,
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    FOREIGN KEY (underlying_instrument_id, underlying_product_code)
        REFERENCES sec_instrument (instrument_id, product_code)
);

CREATE OR REPLACE TABLE sec_instrument_fnd (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code IN ('EQ-FND-ETF', 'EQ-FND-ETP')),
    fund_structure           TEXT NOT NULL CHECK (fund_structure IN ('ETF', 'ETP', 'ETN')),
    tracked_index_name       TEXT,
    is_leveraged             BOOLEAN NOT NULL DEFAULT FALSE,
    is_inverse               BOOLEAN NOT NULL DEFAULT FALSE,
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code)
);

CREATE OR REPLACE TABLE sec_instrument_fut_contract (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code IN ('EQ-FUT-INDEX', 'EQ-FUT-SINGLE')),
    underlying_instrument_id BIGINT NOT NULL,
    underlying_product_code  TEXT NOT NULL,
    root_symbol              TEXT,
    contract_multiplier      NUMERIC CHECK (contract_multiplier > 0),
    settlement_type          TEXT CHECK (settlement_type IN ('CASH', 'PHYSICAL')),
    expiry_date              DATE NOT NULL,
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    FOREIGN KEY (underlying_instrument_id, underlying_product_code)
        REFERENCES sec_instrument (instrument_id, product_code),
    CHECK ((product_code = 'EQ-FUT-INDEX' AND underlying_product_code = 'EQ-SPT-INDEX')
        OR (product_code = 'EQ-FUT-SINGLE'
            AND underlying_product_code IN ('EQ-SPT-COMMON', 'EQ-SPT-DEP-RCPT')))
);

CREATE OR REPLACE TABLE sec_instrument_opt_series (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code = 'EQ-OPT-VANILLA'),
    underlying_instrument_id BIGINT NOT NULL,
    underlying_product_code  TEXT NOT NULL CHECK (underlying_product_code IN
        ('EQ-SPT-COMMON', 'EQ-SPT-PREF', 'EQ-SPT-DEP-RCPT', 'EQ-SPT-INDEX',
         'EQ-FND-ETF', 'EQ-FND-ETP')),
    put_call                 TEXT NOT NULL CHECK (put_call IN ('PUT', 'CALL')),
    strike                   NUMERIC NOT NULL CHECK (strike > 0),                 -- R5, R9
    expiry_date              DATE NOT NULL,
    exercise_style           TEXT NOT NULL CHECK (exercise_style IN
        ('AMERICAN', 'EUROPEAN', 'BERMUDAN')),
    contract_multiplier      NUMERIC CHECK (contract_multiplier > 0),
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    FOREIGN KEY (underlying_instrument_id, underlying_product_code)
        REFERENCES sec_instrument (instrument_id, product_code)
);

-- Forwards and CFDs share one table: both are OTC price-return contracts on one underlying
CREATE OR REPLACE TABLE sec_instrument_fwd_contract (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code IN
        ('EQ-FWD-PRICE-RTN', 'EQ-CFD-PRICE-RTN')),
    underlying_instrument_id BIGINT NOT NULL,
    underlying_product_code  TEXT NOT NULL CHECK (underlying_product_code IN
        ('EQ-SPT-COMMON', 'EQ-SPT-PREF', 'EQ-SPT-DEP-RCPT', 'EQ-SPT-INDEX',
         'EQ-FND-ETF', 'EQ-FND-ETP')),
    settlement_type          TEXT CHECK (settlement_type IN ('CASH', 'PHYSICAL')),
    maturity_date            DATE,
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    FOREIGN KEY (underlying_instrument_id, underlying_product_code)
        REFERENCES sec_instrument (instrument_id, product_code)
);

-- Swaps and portfolio swaps: header plus legs (no notionals; those are trade data)
CREATE OR REPLACE TABLE sec_instrument_swp_contract (
    instrument_id            BIGINT PRIMARY KEY,
    product_code             TEXT NOT NULL CHECK (product_code IN
        ('EQ-SWP-PRICE-RTN', 'EQ-PSW-PRICE-RTN')),
    underlying_instrument_id BIGINT,
    underlying_product_code  TEXT CHECK (underlying_product_code IN
        ('EQ-SPT-COMMON', 'EQ-SPT-PREF', 'EQ-SPT-DEP-RCPT', 'EQ-SPT-INDEX',
         'EQ-FND-ETF', 'EQ-FND-ETP')),
    termination_date         DATE,
    source                   TEXT NOT NULL,
    as_of                    DATE NOT NULL,
    FOREIGN KEY (instrument_id, product_code) REFERENCES sec_instrument (instrument_id, product_code),
    FOREIGN KEY (underlying_instrument_id, underlying_product_code)
        REFERENCES sec_instrument (instrument_id, product_code),
    CHECK ((underlying_instrument_id IS NULL) = (underlying_product_code IS NULL)),
    CHECK (product_code = 'EQ-PSW-PRICE-RTN' OR underlying_instrument_id IS NOT NULL)
);

CREATE OR REPLACE TABLE sec_instrument_swp_leg (
    swap_instrument_id  BIGINT NOT NULL REFERENCES sec_instrument_swp_contract (instrument_id),
    leg_number          INTEGER NOT NULL CHECK (leg_number > 0),
    leg_type            TEXT NOT NULL CHECK (leg_type IN ('RETURN', 'FUNDING')),
    pay_receive         TEXT NOT NULL CHECK (pay_receive IN ('PAY', 'RECEIVE')),
    index_name          TEXT,
    spread_bps          NUMERIC,
    PRIMARY KEY (swap_instrument_id, leg_number)
);

-- Rows that cannot become a golden instrument are quarantined here with a reason code. The queue
-- identifies the source row by file hash and row number and keeps its identifying text; no
-- amounts or values are stored.
CREATE OR REPLACE SEQUENCE seq_sec_exception_queue;
CREATE OR REPLACE TABLE sec_exception_queue (
    exception_id    BIGINT PRIMARY KEY DEFAULT nextval('seq_sec_exception_queue'),
    file_sha256     CHAR(64) NOT NULL,
    row_number      INTEGER NOT NULL,
    name_of_issuer  TEXT,
    title_of_class  TEXT,
    cusip           TEXT,
    reason_code     TEXT NOT NULL CHECK (reason_code IN (
        'UNMAPPED_CLASS', 'AMBIGUOUS_CLASS', 'OPT_SERIES_UNRESOLVED',
        'UNDERLYING_UNRESOLVED', 'INVALID_IDENTIFIER', 'ISSUER_UNRESOLVED', 'VENUE_UNRESOLVED')),
    rule_id         TEXT,
    detail          TEXT,
    UNIQUE (file_sha256, row_number)
);
