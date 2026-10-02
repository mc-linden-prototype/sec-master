---
name: introduction
description: What C.A.S.M is aiming to achieve, a high-level breakdown of Phase 1 (prototype) and Phase 2+ (further build-out).
---

# Introduction

> Index: [README.md](../../README.md)

## What we are aiming to achieve

C.A.S.M (Cross Asset Security Master) is a security master: **reference data only**. It records what
a security is (its identifiers, issuer, classification, listings and relationships to other
instruments) and never what is owned. There are no positions, quantities, values or exposure.

The aim is one consistent, auditable description of every instrument across asset classes, built on:

- a taxonomy (asset class, then product code) as the organizing spine;
- issuers and instruments kept separate and linked by foreign keys;
- one identifier model for every asset type;
- integrity enforced by the database, with bad data quarantined with a reason rather than absorbed.

See [Project scope](1_3-project-scope.md) for the tenets and [Operations flow](1_1-sec-master-ops-flow.md)
for how a security master runs day to day.

## Phase 1: prototype

A static, one-time load that proves the model works. It is not an operational database.

- **Baseline:** the Linden Advisors Form 13F-HR filing, used only as a realistic sample list of instruments,
  plus the master data under `docs/references/`.
- **Scope:** the 17 Tier 1 product codes; a 301-row sample of the filing.
- **Delivers:** the taxonomy and classification rules, the DuckDB schema with integrity rules, golden
  instruments and an exception queue, and an API and UI to browse them.
- **Detail:** [Project scope](1_3-project-scope.md), [Asset classification](2_1-asset-classification.md),
  [Taxonomy](2_2-taxonomy.md), [Database schema](3_1-database-schema.md), [Tech stack](3_2-tech-stack.md),
  [API and UI](3_3-api-ui.md).

## Phase 2+: further build-out

Direction beyond the prototype, not built:

- bitemporal history and corporate-action handling;
- vendor ingestion with source precedence and survivorship;
- a data-quality framework with exception workflows;
- Tier 3 and the remaining asset classes through config-driven product templates;
- distribution through data contracts, a query API and change events;
- licensed classification (GICS) and further identifiers (SEDOL, ISIN, LEI).
- surrounding systems: market data and reference vendors (Bloomberg B-PIPE, LSEG Refinitiv and Reuters,
  ICE, S&P Global Markit, FactSet, Morningstar), a market data platform, and pricing engines per product family
  (equity, fixed income and convertibles, options, futures, swaps and CFDs). Diagram and detail:
  [Operations flow](1_1-sec-master-ops-flow.md) section 10.

The full list is section 13 of [Project scope](1_3-project-scope.md); the operating model behind it is
[Operations flow](1_1-sec-master-ops-flow.md).
