---
name: validate-ui
description: Launch C.A.S.M, drive the UI in a real Chrome browser over the DevTools Protocol, and verify that every screen shows the data the project promises, with screenshots and a written report. Use after any change to the API, the UI or the seed data.
---

# Validate the UI against the database

## What this validates

That the data shown in the browser matches the project: 398 instruments and 22 queued rows, the right
identifiers and venues per instrument, the reference sets (13 loaded venues of 2,883, 158 GICS rows, 17
product codes, 249 countries, 34 ISDA rows), the wiki in reading order with Mermaid diagrams drawn, and no
browser console errors or failed requests.

## Tools used

| Tool | Role |
|---|---|
| `uv run python src/main.py` | Starts the API (9099) and UI (9095); the API rebuilds the database first |
| `.claude/skills/validate-ui/validate_ui.py` | The checks (below) and the report writer |
| Playwright, `channel="chrome"` | Drives the installed Google Chrome over the Chrome DevTools Protocol: navigation, DOM queries, screenshots, console and network listeners |
| urllib | Calls the API directly to compare with what the UI shows |
| `Read` on the PNGs | A human-style look at each screenshot for clarity |

If the Claude-in-Chrome extension tools (`mcp__claude-in-chrome__*`) are available, use them to inspect the
same screens by hand and add anything the script cannot judge (layout, clarity of wording).

## Run it

```
uv run --with playwright python .claude/skills/validate-ui/validate_ui.py
```

It needs Google Chrome installed and internet access (the UI loads Tailwind, fonts, marked and mermaid from
CDNs). It starts the app itself and first stops any copy already running on ports 9099 and 9095; afterwards it
stops the whole process tree. Output:

- `docs/validation/ui-validation-report.md`: each check, pass or fail, with the value seen and the value expected
- `docs/validation/screenshots/*.png`: one per screen

The script exits non-zero if any check fails.

## What it checks

| Screen | Checks |
|---|---|
| API | `/api/health` ok; the totals and the MKS convertible match what the UI shows |
| Securities | All 398 instruments shown (no paging controls anywhere); the identifier, issuer, Und. Security and venue columns, with no always-empty ISIN or CCY column; grid lines both ways; sorting; CUSIP search finds MKS INC 1.25 06/01/2030 with "Detected: CUSIP"; the Details summary names the underlying first; following it shows the breadcrumb `MKS INC 1.... › MKS INC` and the breadcrumb goes back; Governance lists the attributes not held and shows no integrity rules; Lineage cites the 13F; filters (63 warrants, 18 unlisted); an ISIN search says none is held; the Issuers view lists 213 issuers and opens an instrument; the exception queue shows 22 rows with reasons |
| Reference Data | Venues open on the full registry (2,883 rows, in MIC order) and narrow to the 13 loaded; XNAS detail (249 listings); GICS all four levels (262 nodes, with level filter counts 11, 24, 69, 158) with codes, names and parents, and a node's inspector; taxonomy 17 rows with product, asset class and base product codes and names, description and source, and EQ-SPT-COMMON at 201 instruments; countries 249; ISDA 34; the source file and SHA-256 card; no paging controls |
| Wiki | Index first, then 00, 01, 02, 03, 05, 06, 07 in order; tables render; the plan page draws Mermaid SVGs; internal links change page |
| Consistency | The same cell font and size, title size, row (36px) and header heights on Securities and Reference; wiki text and code in the same fonts; the inspector reaches the bottom of the window and the count strip sits at the bottom of a short grid |
| Browser | No console errors, no failed requests |

## After running

Read the report, open the screenshots, and fix any failure at its cause (data, API or UI), then run again.
Say in the summary which tools ran and what the report shows.
