---
name: taxonomy
description: Phase 1 taxonomy: the EQ and FI hierarchy for the 17 product codes, decision trees and regulatory alignment.
---

# Taxonomy (Phase 1 instrument types)

> Index: [README.md](../../README.md) · Plan: [Project scope](1_3-project-scope.md) · Classification: [Asset classification](2_1-asset-classification.md)

The hierarchy, decision trees and regulatory alignment for the 17 Phase 1 product codes only
([Project scope](1_3-project-scope.md) section 4.1). Other asset classes and the deferred Tier 3 equity
codes are listed in [Asset classification](2_1-asset-classification.md).

## 1. Hierarchy

### 1.1 Equity (`EQ`)

**Risk rationale.** Equity products aggregate for beta/delta exposure. ETFs are classified here to
capture total equity market exposure alongside direct stock holdings.

| L1 | Base product | L2 | Sub-product / underlying | L3 | Full code | Source | Description |
|----|--------------|----|--------------------------|----|-----------|--------|-------------|
| EQ | Contract For Difference | CFD | Price Return | PRICE-RTN | `EQ-CFD-PRICE-RTN` | ISDA | Contracts for difference on equities |
| EQ | Forward | FWD | Price Return | PRICE-RTN | `EQ-FWD-PRICE-RTN` | ISDA | Equity forward contracts |
| EQ | Fund | FND | Exchange Traded Fund | ETF | `EQ-FND-ETF` | CASM | Equity ETFs (SPY, QQQ, IWM) |
| EQ | Fund | FND | Exchange Traded Product | ETP | `EQ-FND-ETP` | CASM | Leveraged/inverse equity ETPs (TQQQ, SQQQ) |
| EQ | Future | FUT | Index Future | INDEX | `EQ-FUT-INDEX` | MX3 | Equity index futures |
| EQ | Future | FUT | Single Stock Future | SINGLE | `EQ-FUT-SINGLE` | MX3 | Single stock futures |
| EQ | Option | OPT | Vanilla | VANILLA | `EQ-OPT-VANILLA` | ISDA | Standard equity options (listed and OTC) |
| EQ | Portfolio Swap | PSW | Price Return | PRICE-RTN | `EQ-PSW-PRICE-RTN` | ISDA | Equity portfolio swaps |
| EQ | Spot | SPT | Common Stock | COMMON | `EQ-SPT-COMMON` | CASM | Ordinary common shares |
| EQ | Spot | SPT | Depository Receipt | DEP-RCPT | `EQ-SPT-DEP-RCPT` | CASM | ADRs, GDRs |
| EQ | Spot | SPT | Index | INDEX | `EQ-SPT-INDEX` | CASM | Equity indexes as cash instruments |
| EQ | Spot | SPT | Preferred Stock | PREF | `EQ-SPT-PREF` | CASM | Preferred shares |
| EQ | Spot | SPT | Rights Issue | RIGHTS | `EQ-SPT-RIGHTS` | CASM | Rights issues |
| EQ | Spot | SPT | Unit | UNIT | `EQ-SPT-UNIT` | CASM | Units or structured equity products |
| EQ | Spot | SPT | Warrant | WARRANT | `EQ-SPT-WARRANT` | CASM | Equity warrants |
| EQ | Swap | SWP | Price Return | PRICE-RTN | `EQ-SWP-PRICE-RTN` | ISDA | Standard price-return equity swaps |

16 equity product codes.

### 1.2 Fixed income (`FI`)

**Risk rationale.** Fixed income products aggregate for duration and credit spread risk.

| L1 | Base product | L2 | Sub-product / underlying | L3 | Full code | Source | Description |
|----|--------------|----|--------------------------|----|-----------|--------|-------------|
| FI | Bond | BND | Convertible | CONV | `FI-BND-CONV` | MX3 | Convertible bonds |

1 fixed income product code. A convertible links to an underlying equity instrument (rule R3 in
[Project scope](1_3-project-scope.md) section 7.3).

## 2. Decision trees

### 2.1 Fund classification (equity branch)

```
Is it a pooled investment vehicle (ETF/ETP/ETN)?
│
├─ YES → Primary underlying exposure is equities or stock indices
│   ├─ Standard ETF              → EQ-FND-ETF
│   └─ Leveraged/Inverse/ETN     → EQ-FND-ETP
│
└─ NO → Use the appropriate non-fund code (SPT, FUT, OPT, CFD, FWD, SWP, PSW, BND)
```

Funds are classified by primary underlying exposure (risk-based, see
[Asset classification](2_1-asset-classification.md) section 3). A fund whose exposure is not equity is outside
Phase 1.

### 2.2 Derivative classification (equity branch)

```
Is it a derivative instrument?
│
├─ YES → Underlying asset class is equity → EQ
│   │
│   └─ What is the product structure?
│       ├─ Exchange-traded future
│       │   ├─ On an index                 → EQ-FUT-INDEX
│       │   └─ On a single stock           → EQ-FUT-SINGLE
│       ├─ Option (listed or OTC), vanilla → EQ-OPT-VANILLA
│       ├─ OTC forward                     → EQ-FWD-PRICE-RTN
│       ├─ Contract for difference         → EQ-CFD-PRICE-RTN
│       ├─ Swap
│       │   ├─ Single-instrument price return → EQ-SWP-PRICE-RTN
│       │   └─ Portfolio-level structure      → EQ-PSW-PRICE-RTN
│       └─ Exotic / structured             → outside Phase 1 (Tier 3)
│
└─ NO → Is it a cash/spot instrument?
    ├─ YES → SPT (equity) or BND (convertible bond)
    └─ NO  → Fund/pooled vehicle → section 2.1; otherwise outside Phase 1
```

## 3. Regulatory alignment (Phase 1 scope)

Attributes apply to derivatives only (`FUT`, `OPT`, `CFD`, `FWD`, `SWP`, `PSW`). Spot, fund and
bond codes carry none; that is by design, not a gap. See [Asset classification](2_1-asset-classification.md) section 6.1.

| Framework | Category | Phase 1 L1 | Notes |
|-----------|----------|------------|-------|
| ISDA Product Taxonomy 2.0 | Equity derivatives | EQ | ISDA plus MX3 extensions; the futures codes are MX3. `isda_path` is null for all codes |
| CFTC asset classes | Equity | EQ | |
| EMIR / MiFID II | C5: Equity derivatives | EQ | Held as `mifid_category` only |

## 4. Known gaps

- The issuer convention for `EQ-SPT-INDEX` and for derivatives is undecided (R2); also recorded in
  [Asset classification](2_1-asset-classification.md) section 6.1.
- `EQ-CFD-PRICE-RTN` shares `sec_instrument_fwd_contract` with forwards, so R1 holds without a
  separate CFD table.
- `ref_product_code.isda_path` is null for every code: product codes do not map one-to-one onto
  the rows of `ref_isda_equity_taxonomy` ([Database schema](3_1-database-schema.md) section 4).
