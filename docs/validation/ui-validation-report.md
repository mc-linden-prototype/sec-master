# UI validation report

Run: 2026-10-01 21:52 UTC. Result: **209 of 209 checks passed**; 0 console errors, 0 failed requests.

## Tools used

- `src/main.py`: launched the API (9099) and UI (9095); the API rebuilt the database first
- Playwright driving the installed Google Chrome (`channel="chrome"`) over the Chrome DevTools Protocol: navigation, DOM reads, screenshots, console and network listeners
- urllib: direct API calls to compare with the screen
- Skill: `.claude/skills/validate-ui` (script `validate_ui.py`)

## Checks

| Area | Check | Expected | Seen | Result |
|---|---|---|---|---|
| API | health status | ok | ok | pass |
| API | migrations applied | 6 | 6 | pass |
| API | universe totals | 398 instruments / 22 queued | 398 instruments / 22 queued | pass |
| Securities | every security is shown (no paging) | 398 | 398 | pass |
| Securities | count strip | 398 securities | 398 securities | pass |
| Securities | no pagination controls | 0 | 0 | pass |
| Securities | no 'Items per page' text | absent | absent | pass |
| Securities | grid lines on a body cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Securities | grid lines on a header cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Securities | column Security Name | contains 'Security Name' | found | pass |
| Securities | column Asset Class | contains 'Asset Class' | found | pass |
| Securities | column Issuer | contains 'Issuer' | found | pass |
| Securities | column Und. Security | contains 'Und. Security' | found | pass |
| Securities | column Ticker | contains 'Ticker' | found | pass |
| Securities | column Venue (MIC) | contains 'Venue (MIC)' | found | pass |
| Securities | column CUSIP | contains 'CUSIP' | found | pass |
| Securities | column FIGI | contains 'FIGI' | found | pass |
| Securities | column Country | contains 'Country' | found | pass |
| Securities | column Venue Confidence | contains 'Venue Confidence' | found | pass |
| Securities | column Bloomberg Ticker | contains 'Bloomberg Ticker' | found | pass |
| Securities | column Composite FIGI | contains 'Composite FIGI' | found | pass |
| Securities | column Issuer CIK | contains 'Issuer CIK' | found | pass |
| Securities | no always-empty ISIN column | absent | absent | pass |
| Securities | no always-empty CCY column | absent | absent | pass |
| Securities | tab bar highlights Securities | contains 'border-primary-container' | found | pass |
| Securities | CUSIP search result count | 1 | 1 | pass |
| Securities | identifier type detected | contains 'Detected: CUSIP' | found | pass |
| Securities | convertible detail shows FI-BND-CONV | contains 'FI-BND-CONV' | found | pass |
| Securities | convertible detail shows 1.250% | contains '1.250%' | found | pass |
| Securities | convertible detail shows 2030-06-01 | contains '2030-06-01' | found | pass |
| Securities | convertible detail shows MKSI | contains 'MKSI' | found | pass |
| Securities | convertible detail shows XOFF | contains 'XOFF' | found | pass |
| Securities | convertible detail shows OTC / unlisted | contains 'OTC / unlisted' | found | pass |
| Securities | convertible detail shows Fixed Income / Bond | contains 'Fixed Income / Bond' | found | pass |
| Securities | convertible detail shows 55306NAB0 | contains '55306NAB0' | found | pass |
| Securities | convertible detail shows SIC (EDGAR) | contains 'SIC (EDGAR)' | found | pass |
| Securities | summary with the underlying comes first in Details | Underlying security before Identification | ok | pass |
| Securities | no breadcrumb before a link is followed | 0 | 0 | pass |
| Securities | breadcrumb: the earlier security shortened to 10 characters, then the current one in full | MKS INC 1.... › MKS INC | MKS INC 1.... › MKS INC | pass |
| Securities | the underlying is now shown | MKS INC | MKS INC | pass |
| Securities | the current breadcrumb item is not a link, the earlier one is | 1 link | 1 link | pass |
| Securities | no parent security is shown | absent | absent | pass |
| Securities | clicking the breadcrumb goes back | MKS INC 1.25 06/01/2030 | MKS INC 1.25 06/01/2030 | pass |
| Securities | governance lists ISIN: not held | contains 'ISIN: not held' | found | pass |
| Securities | governance lists SEDOL: not held | contains 'SEDOL: not held' | found | pass |
| Securities | governance lists GICS: not held | contains 'GICS: not held' | found | pass |
| Securities | governance lists LEI: not held | contains 'LEI: not held' | found | pass |
| Securities | integrity rules are not shown in the Securities inspector | absent | absent | pass |
| Securities | lineage cites 13F-HR:0001193125-26-350767 | contains '13F-HR:0001193125-26-350767' | found | pass |
| Securities | lineage cites OPENFIGI | contains 'OPENFIGI' | found | pass |
| Securities | lineage cites SEC_EDGAR | contains 'SEC_EDGAR' | found | pass |
| Securities | lineage cites DEFAULT | contains 'DEFAULT' | found | pass |
| Securities | warrant filter | contains '63 securities' | found | pass |
| Securities | unlisted (XXXX) venue filter | contains '18 securities' | found | pass |
| Securities | sorted descending: first row equals the API's | ZENAS BIOPHARMA INC 2.5 04/01/2032 | ZENAS BIOPHARMA INC 2.5 04/01/2032 | pass |
| Securities | an ISIN is detected | contains 'Detected: ISIN' | found | pass |
| Securities | and the page says none is held | contains 'No ISIN is held' | found | pass |
| Securities | exception queue total | contains '22 queued rows' | found | pass |
| Securities | exception reasons show INVALID_IDENTIFIER (13) | contains 'INVALID_IDENTIFIER (13)' | found | pass |
| Securities | exception reasons show ISSUER_UNRESOLVED (8) | contains 'ISSUER_UNRESOLVED (8)' | found | pass |
| Securities | exception reasons show VENUE_UNRESOLVED (1) | contains 'VENUE_UNRESOLVED (1)' | found | pass |
| Exceptions | no pagination controls | 0 | 0 | pass |
| Exceptions | no 'Items per page' text | absent | absent | pass |
| Exceptions | grid lines on a body cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Exceptions | grid lines on a header cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Securities | issuers view lists every issuer | 213 issuers | 213 issuers | pass |
| Securities | issuers column Issuer | contains 'Issuer' | found | pass |
| Securities | issuers column Type | contains 'Type' | found | pass |
| Securities | issuers column Country | contains 'Country' | found | pass |
| Securities | issuers column CIK | contains 'CIK' | found | pass |
| Securities | issuers column SIC | contains 'SIC' | found | pass |
| Securities | issuers column CUSIP issuer prefix | contains 'CUSIP issuer prefix' | found | pass |
| Securities | issuers column Instruments | contains 'Instruments' | found | pass |
| Issuers | no pagination controls | 0 | 0 | pass |
| Issuers | no 'Items per page' text | absent | absent | pass |
| Issuers | grid lines on a body cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Issuers | grid lines on a header cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Securities | Alphabet issuer detail shows 0001652044 | contains '0001652044' | found | pass |
| Securities | Alphabet issuer detail shows ALPHABET INC CL A | contains 'ALPHABET INC CL A' | found | pass |
| Securities | Alphabet issuer detail shows ALPHABET INC CL C | contains 'ALPHABET INC CL C' | found | pass |
| Securities | Alphabet issuer detail shows GOOGL | contains 'GOOGL' | found | pass |
| Securities | Alphabet issuer detail shows GOOG | contains 'GOOG' | found | pass |
| Securities | Alphabet issuer detail shows 2 instruments | contains '2 instruments' | found | pass |
| Securities | an issuer's instrument opens in the instruments view | ALPHABET INC CL A | ALPHABET INC CL A | pass |
| Reference | the whole registry is shown by default | 2883 | 2883 | pass |
| Reference | no pagination controls | 0 | 0 | pass |
| Reference | no 'Items per page' text | absent | absent | pass |
| Reference | grid lines on a body cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Reference | grid lines on a header cell (vertical, horizontal) | 1px, 1px | 1px, 1px | pass |
| Reference | venues are listed in MIC order | sorted | sorted | pass |
| Reference | left rail shows 13 / 2,883 | contains '13 / 2,883' | found | pass |
| Reference | left rail shows Venues (ISO 10383) | contains 'Venues (ISO 10383)' | found | pass |
| Reference | left rail shows GICS Hierarchy | contains 'GICS Hierarchy' | found | pass |
| Reference | left rail shows Instrument Taxonomy | contains 'Instrument Taxonomy' | found | pass |
| Reference | left rail shows Countries (ISO 3166) | contains 'Countries (ISO 3166)' | found | pass |
| Reference | left rail shows ISDA Equity Taxonomy | contains 'ISDA Equity Taxonomy' | found | pass |
| Reference | left rail shows ISO10383_MIC.xlsx | contains 'ISO10383_MIC.xlsx' | found | pass |
| Reference | left rail shows SHA-256 9d0d3320cb2a | contains 'SHA-256 9d0d3320cb2a' | found | pass |
| Reference | the loaded venues can be narrowed to | 13 | 13 | pass |
| Reference | venue XNAS listed | contains 'XNAS' | found | pass |
| Reference | venue XNYS listed | contains 'XNYS' | found | pass |
| Reference | venue XASE listed | contains 'XASE' | found | pass |
| Reference | venue ARCX listed | contains 'ARCX' | found | pass |
| Reference | venue BATS listed | contains 'BATS' | found | pass |
| Reference | venue EDGX listed | contains 'EDGX' | found | pass |
| Reference | venue IEXG listed | contains 'IEXG' | found | pass |
| Reference | venue XCBO listed | contains 'XCBO' | found | pass |
| Reference | venue XCME listed | contains 'XCME' | found | pass |
| Reference | venue XCBT listed | contains 'XCBT' | found | pass |
| Reference | venue IFUS listed | contains 'IFUS' | found | pass |
| Reference | venue XOFF listed | contains 'XOFF' | found | pass |
| Reference | venue XXXX listed | contains 'XXXX' | found | pass |
| Reference | XNAS detail shows 549300L8X1Q78ERXFD06 | contains '549300L8X1Q78ERXFD06' | found | pass |
| Reference | XNAS detail shows 249 of 398 instruments listed here | contains '249 of 398 instruments listed here' | found | pass |
| Reference | XNAS detail shows EXCHANGE | contains 'EXCHANGE' | found | pass |
| Reference | gics row count | contains '262 rows' | found | pass |
| Reference | gics search finds Energy Equipment & Services | contains 'Energy Equipment & Services' | found | pass |
| Reference | gics grid column Level | contains 'Level' | found | pass |
| Reference | gics grid column Code | contains 'Code' | found | pass |
| Reference | gics grid column Name | contains 'Name' | found | pass |
| Reference | gics grid column Parent Code | contains 'Parent Code' | found | pass |
| Reference | gics grid column Parent | contains 'Parent' | found | pass |
| Reference | no pagination controls | 0 | 0 | pass |
| Reference | no 'Items per page' text | absent | absent | pass |
| Reference | taxonomy row count | contains '17 rows' | found | pass |
| Reference | taxonomy search finds EQ-SPT-COMMON | contains 'EQ-SPT-COMMON' | found | pass |
| Reference | taxonomy grid column Product Code | contains 'Product Code' | found | pass |
| Reference | taxonomy grid column Asset Class Code | contains 'Asset Class Code' | found | pass |
| Reference | taxonomy grid column Asset Class | contains 'Asset Class' | found | pass |
| Reference | taxonomy grid column Base Product Code | contains 'Base Product Code' | found | pass |
| Reference | taxonomy grid column Base Product | contains 'Base Product' | found | pass |
| Reference | taxonomy grid column Description | contains 'Description' | found | pass |
| Reference | taxonomy grid column Source | contains 'Source' | found | pass |
| Reference | no pagination controls | 0 | 0 | pass |
| Reference | no 'Items per page' text | absent | absent | pass |
| Reference | countries row count | contains '249 rows' | found | pass |
| Reference | countries search finds Cayman Islands | contains 'Cayman Islands' | found | pass |
| Reference | no pagination controls | 0 | 0 | pass |
| Reference | no 'Items per page' text | absent | absent | pass |
| Reference | isda row count | contains '34 rows' | found | pass |
| Reference | isda search finds Price Return Basic Performance | contains 'Price Return Basic Performance' | found | pass |
| Reference | no pagination controls | 0 | 0 | pass |
| Reference | no 'Items per page' text | absent | absent | pass |
| Reference | taxonomy row shows EQ-SPT-COMMON | contains 'EQ-SPT-COMMON' | found | pass |
| Reference | taxonomy row shows EQ | contains 'EQ' | found | pass |
| Reference | taxonomy row shows Equity | contains 'Equity' | found | pass |
| Reference | taxonomy row shows SPT | contains 'SPT' | found | pass |
| Reference | taxonomy row shows Spot | contains 'Spot' | found | pass |
| Reference | taxonomy row shows Ordinary common shares | contains 'Ordinary common shares' | found | pass |
| Reference | taxonomy row shows CASM | contains 'CASM' | found | pass |
| Reference | taxonomy inspector: EQ-SPT-COMMON has 201 instruments | contains '201' | found | pass |
| Reference | GICS Sector row 10 shows Sector | contains 'Sector' | found | pass |
| Reference | GICS Sector row 10 shows 10 | contains '10' | found | pass |
| Reference | GICS Sector row 10 shows Energy | contains 'Energy' | found | pass |
| Reference | GICS Industry Group row 1010 shows Industry Group | contains 'Industry Group' | found | pass |
| Reference | GICS Industry Group row 1010 shows 1010 | contains '1010' | found | pass |
| Reference | GICS Industry Group row 1010 shows Energy | contains 'Energy' | found | pass |
| Reference | GICS Industry Group row 1010 shows 10 | contains '10' | found | pass |
| Reference | GICS Industry row 101010 shows Industry | contains 'Industry' | found | pass |
| Reference | GICS Industry row 101010 shows 101010 | contains '101010' | found | pass |
| Reference | GICS Industry row 101010 shows Energy Equipment & Services | contains 'Energy Equipment & Services' | found | pass |
| Reference | GICS Industry row 101010 shows 1010 | contains '1010' | found | pass |
| Reference | GICS Sub-Industry row 10101010 shows Sub-Industry | contains 'Sub-Industry' | found | pass |
| Reference | GICS Sub-Industry row 10101010 shows 10101010 | contains '10101010' | found | pass |
| Reference | GICS Sub-Industry row 10101010 shows Oil & Gas Drilling | contains 'Oil & Gas Drilling' | found | pass |
| Reference | GICS Sub-Industry row 10101010 shows 101010 | contains '101010' | found | pass |
| Reference | GICS Sub-Industry row 10101010 shows Energy Equipment & Services | contains 'Energy Equipment & Services' | found | pass |
| Reference | GICS level filter Sector | 11 | 11 | pass |
| Reference | GICS level filter Industry Group | 24 | 24 | pass |
| Reference | GICS level filter Industry | 69 | 69 | pass |
| Reference | GICS level filter Sub-Industry | 158 | 158 | pass |
| Reference | GICS inspector shows Sector | contains 'Sector' | found | pass |
| Reference | GICS inspector shows Industry Group | contains 'Industry Group' | found | pass |
| Reference | GICS inspector shows Industry | contains 'Industry' | found | pass |
| Reference | GICS inspector shows Sub-Industry | contains 'Sub-Industry' | found | pass |
| Reference | GICS inspector shows Energy Equipment & Services | contains 'Energy Equipment & Services' | found | pass |
| Reference | GICS inspector shows Drilling contractors | contains 'Drilling contractors' | found | pass |
| Wiki | reading order from the API | index first, then sorted | ok | pass |
| Wiki | page 00-sec-master-operations-flow listed | True | True | pass |
| Wiki | page 01-plan-and-deliverable listed | True | True | pass |
| Wiki | page 05-database-design listed | True | True | pass |
| Wiki | page 06-tech-stack listed | True | True | pass |
| Wiki | page 07-api-and-ui listed | True | True | pass |
| Wiki | left rail matches API order and titles | C.A.S.M Security Master \| 00 — Security Master Operations Flow \| 01 — Plan and Deliverable (Phase 1 Prototype) \| 02 — Design Principles, Code Format and Classification \| 03 — Taxonomy (Phase 1 instrument types) \| 05 — Database Design (Phase 1 schema) \| 06 — Tech Stack and Setup \| 07 — API and UI | C.A.S.M Security Master \| 00 — Security Master Operations Flow \| 01 — Plan and Deliverable (Phase 1 Prototype) \| 02 — Design Principles, Code Format and Classification \| 03 — Taxonomy (Phase 1 instrument types) \| 05 — Database Design (Phase 1 schema) \| 06 — Tech Stack and Setup \| 07 — API and UI | pass |
| Wiki | index page has the known gaps | contains 'Known gaps' | found | pass |
| Wiki | plan page draws its Mermaid diagram | >= 1 SVG | 1 SVG | pass |
| Wiki | plan page renders markdown tables | >= 5 | 23 | pass |
| Wiki | no raw mermaid code left | 0 | 0 | pass |
| Wiki | no unresolved .md links on the page reached | 0 | 0 | pass |
| Wiki | 05-database-design renders a heading | True | True | pass |
| Wiki | 06-tech-stack renders a heading | True | True | pass |
| Wiki | 07-api-and-ui renders a heading | True | True | pass |
| Wiki | code blocks have a white background | rgb(255, 255, 255) | rgb(255, 255, 255) | pass |
| Wiki | code block text is dark | r, g, b all < 80 | rgb(22, 22, 22) | pass |
| Consistency | Securities inspector reaches the bottom of the window | >= 980px | 1000px | pass |
| Consistency | Securities pager sits at the bottom with a single result | >= 900px | 1000px | pass |
| Consistency | Securities and Reference agree on cell size | 14px | 14px | pass |
| Consistency | Securities and Reference agree on cell family | "IBM Plex Sans" | "IBM Plex Sans" | pass |
| Consistency | Securities and Reference agree on title size | 16px | 16px | pass |
| Consistency | Securities and Reference agree on row height | 36 | 36 | pass |
| Consistency | Securities and Reference agree on head height | 40 | 40 | pass |
| Consistency | Reference inspector is full height | >= 900px | 952px | pass |
| Consistency | Reference pager sits at the bottom of a short table | >= 900px | 1000px | pass |
| Consistency | Wiki body text uses the same font family | "IBM Plex Sans" | "IBM Plex Sans" | pass |
| Consistency | Wiki body text uses the same font size | 14px | 14px | pass |
| Consistency | Wiki code uses the same monospace family as the tables | "JetBrains Mono" | "JetBrains Mono" | pass |
| Consistency | Wiki code and table identifiers share one monospace family | "JetBrains Mono" | "JetBrains Mono" | pass |
| Browser | console errors | 0 | 0 | pass |
| Browser | failed requests | 0 | 0 | pass |

## Browser console errors

None.

## Failed requests

None.

## Screenshots

- `screenshots/01-securities-default.png`
- `screenshots/02-securities-convertible-details.png`
- `screenshots/02b-securities-underlying-with-breadcrumb.png`
- `screenshots/03-securities-convertible-governance.png`
- `screenshots/04-securities-convertible-lineage.png`
- `screenshots/05-securities-isin-not-held.png`
- `screenshots/06-securities-exception-queue.png`
- `screenshots/06b-securities-issuers.png`
- `screenshots/07-reference-venues.png`
- `screenshots/08-reference-gics.png`
- `screenshots/08b-reference-gics-sector.png`
- `screenshots/09-reference-taxonomy.png`
- `screenshots/10-reference-countries.png`
- `screenshots/11-reference-isda.png`
- `screenshots/12-wiki-index.png`
- `screenshots/13-wiki-plan-mermaid.png`
- `screenshots/14-wiki-database.png`
- `screenshots/14b-wiki-code-block.png`
- `screenshots/15-securities-single-result-full-height.png`
- `screenshots/16-reference-short-table-full-height.png`
