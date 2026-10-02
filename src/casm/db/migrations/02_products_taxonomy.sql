-- Phase 1 taxonomy: 2 asset classes, 9 base products, 17 product codes (see docs/wiki/2_2-taxonomy.md).
-- cftc_asset_class and mifid_category are set for derivatives only; desk_family and isda_path stay
-- null because the taxonomy does not define them.
-- Re-runnable: clears its tables and every table that depends on them (children first) before inserting; run the later seed migrations again afterwards.
DELETE FROM sec_listing;
DELETE FROM sec_instrument_swp_leg;
DELETE FROM sec_instrument_swp_contract;
DELETE FROM sec_instrument_fwd_contract;
DELETE FROM sec_instrument_opt_series;
DELETE FROM sec_instrument_fut_contract;
DELETE FROM sec_instrument_fnd;
DELETE FROM sec_instrument_fi_bond;
DELETE FROM sec_instrument_eq_warrant_right;
DELETE FROM sec_instrument_eq_spt;
DELETE FROM sec_identifier_xref;
DELETE FROM sec_instrument;
DELETE FROM ref_product_code;
DELETE FROM ref_base_product;
DELETE FROM ref_asset_class;

INSERT INTO ref_asset_class (code, name) VALUES ('EQ', 'Equity'), ('FI', 'Fixed Income');

INSERT INTO ref_base_product (code, name, description) VALUES
 ('SPT', 'Spot', 'Spot/cash instruments'),
 ('BND', 'Bond', 'Debt securities with fixed or floating coupons'),
 ('FND', 'Fund', 'Pooled investment vehicles (ETF, ETP)'),
 ('FUT', 'Future', 'Exchange-traded futures'),
 ('OPT', 'Option', 'Listed and OTC options'),
 ('CFD', 'Contract For Difference', 'Cash-settled price difference contracts'),
 ('FWD', 'Forward', 'OTC forward contracts'),
 ('SWP', 'Swap', 'OTC swap contracts'),
 ('PSW', 'Portfolio Swap', 'Portfolio-level swap structures');

INSERT INTO ref_product_code
    (code, asset_class_code, base_product, description, source, subtype_table,
     cftc_asset_class, mifid_category)
VALUES
 ('EQ-SPT-COMMON',    'EQ', 'SPT', 'Ordinary common shares', 'CASM', 'sec_instrument_eq_spt', NULL, NULL),
 ('EQ-SPT-PREF',      'EQ', 'SPT', 'Preferred shares', 'CASM', 'sec_instrument_eq_spt', NULL, NULL),
 ('EQ-SPT-DEP-RCPT',  'EQ', 'SPT', 'ADRs, GDRs', 'CASM', 'sec_instrument_eq_spt', NULL, NULL),
 ('EQ-SPT-INDEX',     'EQ', 'SPT', 'Equity indexes as cash instruments', 'CASM', 'sec_instrument_eq_spt', NULL, NULL),
 ('EQ-SPT-RIGHTS',    'EQ', 'SPT', 'Rights issues', 'CASM', 'sec_instrument_eq_warrant_right', NULL, NULL),
 ('EQ-SPT-WARRANT',   'EQ', 'SPT', 'Equity warrants', 'CASM', 'sec_instrument_eq_warrant_right', NULL, NULL),
 ('EQ-SPT-UNIT',      'EQ', 'SPT', 'Units or structured equity products', 'CASM', 'sec_instrument_eq_warrant_right', NULL, NULL),
 ('EQ-FND-ETF',       'EQ', 'FND', 'Equity ETFs', 'CASM', 'sec_instrument_fnd', NULL, NULL),
 ('EQ-FND-ETP',       'EQ', 'FND', 'Leveraged/inverse equity ETPs and ETNs', 'CASM', 'sec_instrument_fnd', NULL, NULL),
 ('EQ-FUT-INDEX',     'EQ', 'FUT', 'Equity index futures', 'MX3', 'sec_instrument_fut_contract', 'Equity', 'C5'),
 ('EQ-FUT-SINGLE',    'EQ', 'FUT', 'Single stock futures', 'MX3', 'sec_instrument_fut_contract', 'Equity', 'C5'),
 ('EQ-OPT-VANILLA',   'EQ', 'OPT', 'Standard equity options (listed and OTC)', 'ISDA', 'sec_instrument_opt_series', 'Equity', 'C5'),
 ('EQ-CFD-PRICE-RTN', 'EQ', 'CFD', 'Contracts for difference on equities', 'ISDA', 'sec_instrument_fwd_contract', 'Equity', 'C5'),
 ('EQ-FWD-PRICE-RTN', 'EQ', 'FWD', 'Equity forward contracts', 'ISDA', 'sec_instrument_fwd_contract', 'Equity', 'C5'),
 ('EQ-SWP-PRICE-RTN', 'EQ', 'SWP', 'Standard price-return equity swaps', 'ISDA', 'sec_instrument_swp_contract', 'Equity', 'C5'),
 ('EQ-PSW-PRICE-RTN', 'EQ', 'PSW', 'Equity portfolio swaps', 'ISDA', 'sec_instrument_swp_contract', 'Equity', 'C5'),
 ('FI-BND-CONV',      'FI', 'BND', 'Convertible bonds', 'MX3', 'sec_instrument_fi_bond', NULL, NULL);
