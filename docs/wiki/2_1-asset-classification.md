---
name: asset-classification
description: Classification design: principles, product-code format, asset classes, base products and instrument codes, with Phase 1 items bold and underlined.
---

# Design Principles, Code Format and Classification

> Index: [README.md](../../README.md) · Plan: [Project scope](1_3-project-scope.md)

**IMPORTANT.** <u>**BOLD AND UNDERLINED = Phase 1 - Prototype Deliverable**</u>. Plain text = kept for reference and deferred to Phase 2 - Further Build Out.

## 1. Design principles

| Principle | Description | Phase 1 |
|-----------|-------------|---------|
| <u>**Instrument-type focus**</u> | Classification reflects the economic and trading characteristics of the instrument, not only its underlying asset | Yes |
| <u>**Risk-based classification**</u> | Pooled vehicles (ETFs, ETPs, ETCs) are classified under their underlying asset class, for proper risk aggregation | Yes (`EQ-FND-*`) |
| <u>**Regulatory alignment**</u> | Taxonomy follows ISDA, CFTC, EMIR, MiFID II and SFTR for derivatives and financing transactions; attributes are carried on the product-code row | Yes (equity scope) |
| <u>**Consistent risk aggregation**</u> | Instruments on the same underlying link to a shared issuer/underlying entity | Yes (issuer and underlying FKs) |
| <u>**Data integrity**</u> | Classification comes from a lookup table; instruments reference it by foreign key | Yes |
| <u>**Code consistency**</u> | Fixed code shapes per level (section 2) | Yes |
| <u>**Venue and OTC support**</u> | Venue is never part of a product code: listing-specific attributes sit on a separate listing row per venue, and OTC is derived from the venue type | Yes (`sec_listing`, `ref_venue`); trading calendars Phase 2 |
| Scalability | One core instrument table, JSON for sparse attributes, extension tables for dense product-specific fields | Partly (subtype tables; JSON only for warrant terms) |
| Tokenized assets | Treated like non-tokenized counterparts, flagged and linked to a blockchain | Phase 2 |

## 2. Code format

```
LEVEL1-LEVEL2-LEVEL3
```

Example: <u>**`EQ-FND-ETF`**</u> = Equity, Fund, Exchange Traded Fund.

| Level | Name | Characters | Purpose | Example values |
|-------|------|------------|---------|----------------|
| 1 | Asset Class | 2 uppercase | Broad asset class, for risk bucketing | <u>**EQ**</u>, <u>**FI**</u>, CR, CO, DA, FX, IR |
| 2 | Base Product | 3 uppercase | Product structure or wrapper type | <u>**SPT**</u>, <u>**BND**</u>, <u>**FND**</u>, <u>**FUT**</u>, <u>**OPT**</u>, <u>**CFD**</u>, <u>**FWD**</u>, <u>**SWP**</u>, <u>**PSW**</u> |
| 3 | Sub-Product / Underlying | up to 10 | Qualifies the product, incorporating sub-types | <u>**COMMON**</u>, <u>**CONV**</u>, <u>**ETF**</u>, <u>**VANILLA**</u>, <u>**PRICE-RTN**</u>, <u>**DEP-RCPT**</u>, CDX |

Level 3 may itself contain a hyphen (<u>**`EQ-SPT-DEP-RCPT`**</u>, <u>**`EQ-CFD-PRICE-RTN`**</u>), so a
code is split by position, not on every `-`: level 1 is the first 2 characters, level 2 the next 3,
and level 3 is everything after the second hyphen.

## 3. Classification approach

Classification is by **risk**, not legal structure:

| Approach | Effect | Decision |
|----------|--------|----------|
| Legal structure (all ETFs under "Funds") | Matches fund registration but separates an equity ETF from equities | Not adopted |
| Risk-based (equity ETF under Equity) | Proper risk bucketing; needs analysis of the underlying | Adopted |

```
EQ-SPT-COMMON   direct ownership of a share          -> EQUITY risk bucket
EQ-FND-ETF      ownership of a fund holding shares   -> EQUITY risk bucket
```

## 4. Asset classes (Level 1)

| L1 | Asset class | Description | Phase 1 |
|----|-------------|-------------|---------|
| <u>**EQ**</u> | <u>**Equity**</u> | <u>**Cash equities, equity derivatives, equity funds**</u> | <u>**Yes**</u> |
| <u>**FI**</u> | <u>**Fixed Income**</u> | <u>**Bonds (here: convertibles), money market instruments, securitized products**</u> | <u>**Yes (`FI-BND-CONV` only)**</u> |
| CO | Commodity | Physical and financial commodities: energy, metals, agriculture, LNG | Phase 2 |
| CR | Credit | CDS, indices, tranches, CDOs | Phase 2 |
| DA | Digital Asset | Native tokens, stablecoins, CBDCs, tokenized securities | Phase 2 |
| FD | Funds | Multi-asset funds, mutual funds, UCITS | Phase 2 |
| FX | Foreign Exchange | Spot FX, forwards, options, swaps, cross-currency swaps | Phase 2 |
| IN | Inflation | Inflation swaps, caps, floors | Phase 2 |
| IR | Interest Rate | Single-currency swaps, swaptions, futures, FRAs | Phase 2 |
| IS | Islamic Finance | Sharia-compliant instruments (Sukuk, Murabaha, etc.) | Phase 2 |
| PV | Private Investments | Private equity, private debt, venture capital, direct lending | Phase 2 |
| SF | Securities Finance | Repo, securities lending, buy-sell back, margin lending | Phase 2 |

## 5. Base products (Level 2)

| L2 | Base product | Description | Used in | Phase 1 |
|----|--------------|-------------|---------|---------|
| <u>**SPT**</u> | <u>**Spot**</u> | <u>**Spot/cash instruments**</u> | <u>**CO, DA, EQ, FX**</u> | <u>**Yes (EQ)**</u> |
| <u>**BND**</u> | <u>**Bond**</u> | <u>**Debt securities with fixed or floating coupons**</u> | <u>**FI, IS**</u> | <u>**Yes (FI)**</u> |
| <u>**FND**</u> | <u>**Fund**</u> | <u>**Pooled investment vehicles (ETF, ETP, ETC, MF)**</u> | <u>**CO, DA, EQ, FI, FD**</u> | <u>**Yes (EQ)**</u> |
| <u>**FUT**</u> | <u>**Future**</u> | <u>**Exchange-traded futures**</u> | <u>**CO, DA, EQ, IR**</u> | <u>**Yes (EQ)**</u> |
| <u>**OPT**</u> | <u>**Option**</u> | <u>**Listed and OTC options**</u> | <u>**CO, DA, EQ, FX, IR**</u> | <u>**Yes (EQ)**</u> |
| <u>**CFD**</u> | <u>**Contract For Difference**</u> | <u>**Cash-settled price difference contracts**</u> | <u>**EQ**</u> | <u>**Yes**</u> |
| <u>**FWD**</u> | <u>**Forward**</u> | <u>**OTC forward contracts**</u> | <u>**CO, DA, EQ, FX, IR, IS**</u> | <u>**Yes (EQ)**</u> |
| <u>**SWP**</u> | <u>**Swap**</u> | <u>**OTC swap contracts**</u> | <u>**CO, DA, EQ, FX, IN, IR**</u> | <u>**Yes (EQ)**</u> |
| <u>**PSW**</u> | <u>**Portfolio Swap**</u> | <u>**Portfolio-level swap structures**</u> | <u>**EQ**</u> | <u>**Yes**</u> |
| BSB | Buy-Sell Back | Buy-sell back and sell-buy back transactions | SF | Phase 2 |
| CAP | Cap Floor | Inflation caps and floors (interest rate caps and floors sit under `IR-OPT-CAPFLOOR`) | IN | Phase 2 |
| CDO | CDO | Collateralized debt obligations | CR | Phase 2 |
| CRB | Credit Bond | Credit-linked bonds and notes | CR | Phase 2 |
| DBT | Debt | Private debt instruments | PV | Phase 2 |
| EQT | Equity | Private equity instruments | PV | Phase 2 |
| EXO | Exotic | Exotic/bespoke derivatives | CR | Phase 2 |
| IDX | Index | Credit index products | CR | Phase 2 |
| LSE | Lease | Lease financing structures | IS | Phase 2 |
| MLN | Margin Lending | Margin lending transactions | SF | Phase 2 |
| MMK | Money Market | Short-term money market instruments | FI | Phase 2 |
| PRT | Partnership | Partnership structures | IS | Phase 2 |
| RPO | Repo | Repurchase agreements | SF | Phase 2 |
| SEC | Securitized | Asset-backed and mortgage-backed securities | FI | Phase 2 |
| SLN | Securities Lending | Securities lending and borrowing | SF | Phase 2 |
| SNG | Single Name | Single-name credit derivatives | CR | Phase 2 |
| STR | Structured | Structured products | CO | Phase 2 |
| SWN | Swaption | Options on swaps | CR | Phase 2 |
| SYN | Synthetic Finance | Synthetic financing structures | SF | Phase 2 |
| TRD | Trade | Trade finance structures | IS | Phase 2 |
| TRN | Index Tranche | Credit index tranches | CR | Phase 2 |

## 6. Instruments (Level 3)

### 6.1 Phase 1 instrument types (17 product codes)

Checked against the 13F (638 rows: `RT` 261, `COM` 243, `SDBCV` 133, `ADR` 1; no `putCall` rows). "Source" is the
standard the row comes from; "Subtype table" holds the instrument's terms ([Project scope](1_3-project-scope.md) section 7.1).

| Full code | Instrument | Source | Subtype table | In the 13F |
|-----------|------------|--------|---------------|------------|
| <u>**`EQ-SPT-COMMON`**</u> | <u>**Ordinary common shares**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_spt`**</u> | <u>**Yes** (`COM`; includes non-US `ORD SHS` and share classes)</u> |
| <u>**`EQ-SPT-PREF`**</u> | <u>**Preferred shares**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_spt`**</u> | <u>**No**</u> |
| <u>**`EQ-SPT-DEP-RCPT`**</u> | <u>**ADRs, GDRs**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_spt`**</u> | <u>**Yes** (1 `ADR` row)</u> |
| <u>**`EQ-SPT-RIGHTS`**</u> | <u>**Rights issues**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_warrant_right`**</u> | <u>**Yes** (under `RT`)</u> |
| <u>**`EQ-SPT-WARRANT`**</u> | <u>**Equity warrants**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_warrant_right`**</u> | <u>**Yes** (also under `RT`)</u> |
| <u>**`EQ-SPT-UNIT`**</u> | <u>**Units or structured equity products**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_warrant_right`**</u> | <u>**Yes** (1 row, filed under `COM`)</u> |
| <u>**`EQ-SPT-INDEX`**</u> | <u>**Equity indexes as cash instruments**</u> | <u>**CASM**</u> | <u>**`sec_instrument_eq_spt`**</u> | <u>**No** (reference data, not a holding)</u> |
| <u>**`EQ-FND-ETF`**</u> | <u>**Equity ETFs (SPY, QQQ, IWM)**</u> | <u>**CASM**</u> | <u>**`sec_instrument_fnd`**</u> | <u>**No**</u> |
| <u>**`EQ-FND-ETP`**</u> | <u>**Leveraged/inverse equity ETPs and ETNs (TQQQ, SQQQ)**</u> | <u>**CASM**</u> | <u>**`sec_instrument_fnd`**</u> | <u>**No**</u> |
| <u>**`EQ-FUT-INDEX`**</u> | <u>**Equity index futures**</u> | <u>**MX3**</u> | <u>**`sec_instrument_fut_contract`**</u> | <u>**No** (outside 13F scope)</u> |
| <u>**`EQ-FUT-SINGLE`**</u> | <u>**Single stock futures**</u> | <u>**MX3**</u> | <u>**`sec_instrument_fut_contract`**</u> | <u>**No** (outside 13F scope)</u> |
| <u>**`EQ-OPT-VANILLA`**</u> | <u>**Standard equity options (listed and OTC)**</u> | <u>**ISDA**</u> | <u>**`sec_instrument_opt_series`**</u> | <u>**No** (no `putCall` rows in this file)</u> |
| <u>**`EQ-CFD-PRICE-RTN`**</u> | <u>**Contracts for difference on equities**</u> | <u>**ISDA**</u> | <u>**`sec_instrument_fwd_contract`**</u> | <u>**No** (outside 13F scope)</u> |
| <u>**`EQ-FWD-PRICE-RTN`**</u> | <u>**Equity forward contracts**</u> | <u>**ISDA**</u> | <u>**`sec_instrument_fwd_contract`**</u> | <u>**No** (outside 13F scope)</u> |
| <u>**`EQ-SWP-PRICE-RTN`**</u> | <u>**Standard price-return equity swaps**</u> | <u>**ISDA**</u> | <u>**`sec_instrument_swp_contract`, `sec_instrument_swp_leg`**</u> | <u>**No** (outside 13F scope)</u> |
| <u>**`EQ-PSW-PRICE-RTN`**</u> | <u>**Equity portfolio swaps**</u> | <u>**ISDA**</u> | <u>**`sec_instrument_swp_contract`, `sec_instrument_swp_leg`**</u> | <u>**No** (outside 13F scope)</u> |
| <u>**`FI-BND-CONV`**</u> | <u>**Convertible bonds**</u> | <u>**MX3**</u> | <u>**`sec_instrument_fi_bond`**</u> | <u>**Yes** (`SDBCV`, 133 rows, amounts in `PRN`)</u> |

**Findings from the 13F check**

- **`RT` is not only rights.** It mixes SPAC rights (`... RTS`) with warrants (`... W EXP 11/30/202`, `... CW28`,
  `... WT`), and many names carry no marker. Title of class cannot separate `EQ-SPT-RIGHTS` from
  `EQ-SPT-WARRANT`; the name and reference data (OpenFIGI security type) decide, and an undecidable row is queued.
- **`UNIT` hides under `COM`** (`WILCO 63 CORP UNIT`), so the issuer name is a second classification signal.
- **Fixed-income terms are in the name** (`A10 NETWORKS INC 2.75 04/01/2030 144A`; `0` is zero coupon; names are
  truncated near 30 characters). No structured terms exist; parsing them is deferred
  ([Project scope](1_3-project-scope.md) section 13).
- **Convertible preferred is `EQ-SPT-PREF`**, not `FI-BND-CONV`. **ETP includes ETNs**; physical commodity ETCs are
  `CO-FND-ETC` (Phase 2). **Trusts and REITs are not funds** (`KITE REALTY GROUP TRUST` is common stock).
- **Regulatory attributes fit only derivatives** (`FUT`, `OPT`, `CFD`, `FWD`, `SWP`, `PSW`); they are null by design
  for `SPT`, `FND`, `BND`. The futures codes are MX3 extensions, so their ISDA path is null.
- **CFDs share the forward table** (`sec_instrument_fwd_contract`): R1 needs one subtype row per instrument, and a
  CFD is an OTC price-return contract like a forward ([Database schema](3_1-database-schema.md) section 4).
- **Open: issuer of an index or derivative.** R2 requires an `issuer_id`, but an index or exchange/OTC derivative has
  no issuer in the usual sense; the convention (index provider, or the underlying's issuer) is undecided.

### 6.2 Phase 2 equity codes (Tier 3, deferred)

| Full code | Instrument | Phase 1 |
|-----------|------------|---------|
| `EQ-OPT-ACCUM` | Equity accumulators | Phase 2 (Tier 3) |
| `EQ-OPT-AUTOCALL` | Autocallable equity options | Phase 2 (Tier 3) |
| `EQ-OPT-BARRIER` | Barrier options (KI, KO) | Phase 2 (Tier 3) |
| `EQ-OPT-CLIQUET` | Cliquet/ratchet options | Phase 2 (Tier 3) |
| `EQ-OPT-DECUM` | Equity decumulators | Phase 2 (Tier 3) |
| `EQ-OPT-DIV` | Dividend options | Phase 2 (Tier 3) |
| `EQ-OPT-EXOTIC` | Exotic equity options | Phase 2 (Tier 3) |
| `EQ-OPT-LOOKBACK` | Lookback options | Phase 2 (Tier 3) |
| `EQ-OPT-VAR` | Variance options on equities | Phase 2 (Tier 3) |
| `EQ-OPT-VOL` | Volatility options on equities | Phase 2 (Tier 3) |
| `EQ-SWP-DIV` | Dividend swaps on equities | Phase 2 (Tier 3) |
| `EQ-SWP-VAR` | Variance swaps on equities | Phase 2 (Tier 3) |
| `EQ-SWP-VOL` | Volatility swaps on equities | Phase 2 (Tier 3) |

### 6.3 Fixed income bonds (`FI-BND-*`)

| Full code | Instrument | Phase 1 |
|-----------|------------|---------|
| <u>**`FI-BND-CONV`**</u> | <u>**Convertible bonds**</u> | <u>**Yes**</u> |
| `FI-BND-CORP-FIX` | Fixed-rate corporate bonds | Phase 2 |
| `FI-BND-CORP-FLT` | Floating-rate corporate notes | Phase 2 |
| `FI-BND-COVERED` | Covered bonds | Phase 2 |
| `FI-BND-EM` | Emerging market sovereign bonds | Phase 2 |
| `FI-BND-GOVT` | Sovereign and treasury bonds | Phase 2 |
| `FI-BND-HY` | High yield corporate bonds | Phase 2 |
| `FI-BND-INFL` | Inflation-linked bonds | Phase 2 |
| `FI-BND-MUNI` | Municipal and supranational bonds | Phase 2 |
| `FI-BND-STRUCT` | Structured notes and EMTNs | Phase 2 |

## 7. Source attribution

| Source code | Full name | Description |
|-------------|-----------|-------------|
| ISDA | ISDA Product Taxonomy 2.0 | Standard for OTC derivatives; primary source for derivatives |
| CFTC | CFTC Asset Classes | Regulatory classifications |
| ICMA | ICMA Standards | Fixed income standards |
| SFTR | Securities Financing Transactions Regulation | EU classification of financing transactions |
| MX3 | Murex MX.3 asset classification | Gap-filling operational coverage |
| Project extensions | Risk-based and emerging asset classes | Additions where the standards do not cover |

The product-code row holds `cftc_asset_class`, `mifid_category` and `isda_path`; where the taxonomy
does not define one it stays null and is reported as a gap (see
[Project scope](1_3-project-scope.md) section 15). CFI and EMIR/SFTR flags are not held.
