"""Launch C.A.S.M, drive the UI in Google Chrome over the DevTools Protocol, and verify the data on screen.

Run: uv run --with playwright python .claude/skills/validate-ui/validate_ui.py
Writes docs/validation/ui-validation-report.md and docs/validation/screenshots/*.png.
"""

import json
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT: Path = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))  # the repo package is not installed
from casm.ports import free_ports, stop_pid  # noqa: E402

OUT: Path = ROOT / "docs" / "validation"
SHOTS: Path = OUT / "screenshots"
API: str = "http://127.0.0.1:9099"
UI: str = "http://127.0.0.1:9095"
WAIT_MS: int = 20_000

results: list[tuple[str, str, str, str, bool]] = []  # area, check, expected, seen, ok
console_errors: list[str] = []
failed_requests: list[str] = []


def record(
    area: str, check: str, expected: str, seen: str, ok: bool | None = None
) -> None:
    passed: bool = (expected == seen) if ok is None else ok
    results.append((area, check, expected, seen, passed))
    print(
        f"  [{'ok' if passed else 'FAIL'}] {area}: {check} (expected {expected!r}, saw {seen!r})"
    )


def contains(area: str, check: str, needle: str, text: str) -> None:
    record(
        area,
        check,
        f"contains {needle!r}",
        "found" if needle in text else f"missing; text starts {text[:80]!r}",
        needle in text,
    )


def api_json(path: str) -> object:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as response:
        return json.load(response)


def wait_text(page: Page, selector: str, needle: str) -> None:
    page.wait_for_function(
        "([sel, txt]) => (document.querySelector(sel)?.innerText || '').includes(txt)",
        arg=[selector, needle],
        timeout=WAIT_MS,
    )


def wait_diagrams_drawn(page: Page) -> None:
    """Wait until every Mermaid diagram on the wiki page has finished drawing (Mermaid marks it processed)."""
    page.wait_for_function(
        "() => document.querySelectorAll('#wikiArticle .mermaid:not([data-processed])').length === 0",
        timeout=WAIT_MS,
    )


GRID_COLUMNS: dict[str, tuple[str, ...]] = {
    "taxonomy": (
        "Product Code",
        "Asset Class Code",
        "Asset Class",
        "Base Product Code",
        "Base Product",
        "Description",
        "Source",
    ),
    "gics": ("Level", "Code", "Name", "Parent Code", "Parent"),
}


def no_pagination(page: Page, area: str) -> None:
    """No grid is paged: there are no paging controls anywhere on the screen."""
    controls = page.locator("[data-page], [data-page-size]").count()
    record(area, "no pagination controls", "0", str(controls))
    record(
        area,
        "no 'Items per page' text",
        "absent",
        "present" if "Items per page" in page.inner_text("body") else "absent",
    )


def grid_lines(page: Page, area: str, scope: str) -> None:
    """Grid lines both ways: every body cell and header cell has a right and a bottom border."""
    for label, selector in (
        ("body cell", f"{scope} tbody tr td"),
        ("header cell", f"{scope} thead th"),
    ):
        widths = page.eval_on_selector(
            selector,
            "el => { const s = getComputedStyle(el); return [s.borderRightWidth, s.borderBottomWidth]; }",
        )
        record(
            area,
            f"grid lines on a {label} (vertical, horizontal)",
            "1px, 1px",
            ", ".join(widths),
        )


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False)


def start_app() -> subprocess.Popen[bytes]:
    # Stop any copy that is already running first, so a stale server can never answer in place of the new one.
    free_ports(host="127.0.0.1", ports=[9099, 9095])
    proc: subprocess.Popen[bytes] = subprocess.Popen(
        [sys.executable, str(ROOT / "src" / "main.py")],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline: float = time.time() + 90
    while time.time() < deadline:
        try:
            if api_json("/api/health"):
                urllib.request.urlopen(f"{UI}/config.js", timeout=5).read()
                return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("The app did not become healthy within 90 seconds.")


def validate_api() -> None:
    health = api_json("/api/health")
    record("API", "health status", "ok", str(health["status"]))
    record("API", "migrations applied", "6", str(len(health["migrations"])))
    totals = api_json("/api/v1/securities/filters")["totals"]
    record(
        "API",
        "universe totals",
        "398 instruments / 22 queued",
        f"{totals['instruments']} instruments / {totals['exceptions']} queued",
    )


def validate_securities(page: Page) -> None:
    area = "Securities"
    page.goto(f"{UI}/#/securities")
    page.wait_for_selector("#tableArea tbody tr[data-id]", timeout=WAIT_MS)
    wait_text(page, "#rowCount", "398 securities")
    shot(page, "01-securities-default")
    record(
        area,
        "every security is shown (no paging)",
        "398",
        str(page.locator("#tableArea tbody tr[data-id]").count()),
    )
    record(area, "count strip", "398 securities", page.inner_text("#rowCount").strip())
    no_pagination(page, area)
    grid_lines(page, area, "#tableArea")
    headers = " | ".join(page.locator("#tableArea thead th").all_inner_texts())
    for column in (
        "Security Name",
        "Asset Class",
        "Issuer",
        "Und. Security",
        "Ticker",
        "Venue (MIC)",
        "CUSIP",
        "FIGI",
        "Country",
        "Venue Confidence",
        "Bloomberg Ticker",
        "Composite FIGI",
        "Issuer CIK",
    ):
        contains(area, f"column {column}", column, headers)
    for empty_column in (
        "ISIN",
        "CCY",
    ):  # no source gave these, so no always-empty column
        record(
            area,
            f"no always-empty {empty_column} column",
            "absent",
            "absent" if empty_column not in headers else "present",
        )
    contains(
        area,
        "tab bar highlights Securities",
        "border-primary-container",
        page.get_attribute("#mainNav a[data-route=securities]", "class") or "",
    )

    page.fill("#searchInput", "55306NAB0")
    wait_text(page, "#rowCount", "1 security")
    record(
        area,
        "CUSIP search result count",
        "1",
        str(page.locator("#tableArea tbody tr[data-id]").count()),
    )
    contains(
        area, "identifier type detected", "Detected: CUSIP", page.inner_text("#detected")
    )
    wait_text(page, "#inspector", "MKS INC 1.25 06/01/2030")
    inspector = page.inner_text("#inspector")
    for needle in (
        "FI-BND-CONV",
        "1.250%",
        "2030-06-01",
        "MKSI",
        "XOFF",
        "OTC / unlisted",
        "Fixed Income / Bond",
        "55306NAB0",
        "SIC (EDGAR)",
    ):
        contains(area, f"convertible detail shows {needle}", needle, inspector)
    shot(page, "02-securities-convertible-details")
    lowered = inspector.lower()  # section titles are uppercased by CSS
    summary_first = lowered.index("underlying security") < lowered.index("identification")
    record(
        area,
        "summary with the underlying comes first in Details",
        "Underlying security before Identification",
        "ok" if summary_first else "wrong order",
        summary_first,
    )
    record(
        area,
        "no breadcrumb before a link is followed",
        "0",
        str(page.locator("#trail").count()),
    )
    page.click("#inspector a[data-open]")  # the underlying security
    wait_text(page, "#trail", "MKS INC")
    trail = page.inner_text("#trail")
    record(
        area,
        "breadcrumb: the earlier security shortened to 10 characters, then the current one in full",
        "MKS INC 1.... › MKS INC",
        " ".join(trail.split()),
    )
    record(
        area, "the underlying is now shown", "MKS INC", page.inner_text("#inspector h2")
    )
    record(
        area,
        "the current breadcrumb item is not a link, the earlier one is",
        "1 link",
        f"{page.locator('#trail a').count()} link",
    )
    record(
        area,
        "no parent security is shown",
        "absent",
        (
            "present"
            if "parent securit" in page.inner_text("#inspector").lower()
            else "absent"
        ),
    )
    shot(page, "02b-securities-underlying-with-breadcrumb")
    page.click("#trail a[data-crumb]")
    page.wait_for_function("() => !document.querySelector('#trail')")
    record(
        area,
        "clicking the breadcrumb goes back",
        "MKS INC 1.25 06/01/2030",
        page.inner_text("#inspector h2"),
    )
    page.click("#inspector [data-tab=governance]")
    gov = page.inner_text("#inspector")
    for needle in (
        "ISIN: not held",
        "SEDOL: not held",
        "GICS: not held",
        "LEI: not held",
    ):
        contains(area, f"governance lists {needle}", needle, gov)
    record(
        area,
        "integrity rules are not shown in the Securities inspector",
        "absent",
        "present" if "integrity rules" in gov.lower() else "absent",
    )
    shot(page, "03-securities-convertible-governance")
    page.click("#inspector [data-tab=lineage]")
    lineage = page.inner_text("#inspector")
    for needle in ("13F-HR:0001193125-26-350767", "OPENFIGI", "SEC_EDGAR", "DEFAULT"):
        contains(area, f"lineage cites {needle}", needle, lineage)
    shot(page, "04-securities-convertible-lineage")

    page.click("#clearAll")
    wait_text(page, "#rowCount", "398 securities")
    page.select_option("#fProduct", "EQ-SPT-WARRANT")
    wait_text(page, "#rowCount", "63 securities")
    contains(area, "warrant filter", "63 securities", page.inner_text("#rowCount"))
    page.select_option("#fProduct", "")
    page.select_option("#fMic", "XXXX")
    wait_text(page, "#rowCount", "18 securities")
    contains(
        area,
        "unlisted (XXXX) venue filter",
        "18 securities",
        page.inner_text("#rowCount"),
    )
    page.click("#clearAll")
    wait_text(page, "#rowCount", "398 securities")

    page.click(
        "#tableArea th[data-sort=name]"
    )  # default is ascending: one click sorts descending
    page.wait_for_function(
        "() => document.querySelector('#tableArea th[data-sort=name] .text-primary')"
        "?.innerText === 'arrow_downward'"
    )
    expected_first = api_json("/api/v1/securities?sort=name&direction=desc")["items"][0][
        "name"
    ]
    time.sleep(0.8)
    seen_first = page.locator("#tableArea tbody tr[data-id] td").first.inner_text()
    record(
        area, "sorted descending: first row equals the API's", expected_first, seen_first
    )
    page.click("#tableArea th[data-sort=name]")

    page.fill("#searchInput", "US0378331005")
    wait_text(page, "#note", "ISIN")
    contains(area, "an ISIN is detected", "Detected: ISIN", page.inner_text("#detected"))
    contains(
        area,
        "and the page says none is held",
        "No ISIN is held",
        page.inner_text("#note"),
    )
    shot(page, "05-securities-isin-not-held")
    page.click("#clearAll")

    page.click("[data-view=exceptions]")
    wait_text(page, "#tableArea", "INVALID_IDENTIFIER (13)")
    contains(
        area, "exception queue total", "22 queued rows", page.inner_text("#rowCount")
    )
    for needle in (
        "INVALID_IDENTIFIER (13)",
        "ISSUER_UNRESOLVED (8)",
        "VENUE_UNRESOLVED (1)",
    ):
        contains(
            area,
            f"exception reasons show {needle}",
            needle,
            page.inner_text("#tableArea"),
        )
    shot(page, "06-securities-exception-queue")
    no_pagination(page, "Exceptions")
    grid_lines(page, "Exceptions", "#tableArea")

    page.click("[data-view=issuers]")
    wait_text(page, "#rowCount", "213 issuers")
    record(
        area,
        "issuers view lists every issuer",
        "213 issuers",
        page.inner_text("#rowCount").strip(),
    )
    headers = " | ".join(page.locator("#tableArea thead th").all_inner_texts())
    for column in (
        "Issuer",
        "Type",
        "Country",
        "CIK",
        "SIC",
        "CUSIP issuer prefix",
        "Instruments",
    ):
        contains(area, f"issuers column {column}", column, headers)
    no_pagination(page, "Issuers")
    grid_lines(page, "Issuers", "#tableArea")
    page.fill("#searchInput", "alphabet")
    wait_text(page, "#rowCount", "1 issuer")
    wait_text(page, "#inspector", "Alphabet Inc.")
    issuer_text = page.inner_text("#inspector")
    for needle in (
        "0001652044",
        "ALPHABET INC CL A",
        "ALPHABET INC CL C",
        "GOOGL",
        "GOOG",
        "2 instruments",
    ):
        contains(area, f"Alphabet issuer detail shows {needle}", needle, issuer_text)
    shot(page, "06b-securities-issuers")
    page.click("#inspector a[data-open]")
    page.wait_for_function(
        "() => document.querySelector('#inspector h2')?.innerText === 'ALPHABET INC CL A'"
    )
    record(
        area,
        "an issuer's instrument opens in the instruments view",
        "ALPHABET INC CL A",
        page.inner_text("#inspector h2"),
    )


def validate_reference(page: Page) -> None:
    area = "Reference"
    page.goto(f"{UI}/#/reference/venues")
    page.wait_for_selector("#refTable tbody tr", timeout=WAIT_MS)
    wait_text(page, "#refRowCount", "2,883 venues in the ISO 10383 registry")
    record(
        area,
        "the whole registry is shown by default",
        "2883",
        str(page.locator("#refTable tbody tr").count()),
    )
    no_pagination(page, area)
    grid_lines(page, area, "#refTable")
    mics = page.locator("#refTable tbody tr td:first-child").all_inner_texts()
    record(
        area,
        "venues are listed in MIC order",
        "sorted",
        "sorted" if mics == sorted(mics) else "not sorted",
        mics == sorted(mics),
    )
    rail = page.inner_text("aside")
    for needle in (
        "13 / 2,883",
        "Venues (ISO 10383)",
        "GICS Hierarchy",
        "Instrument Taxonomy",
        "Countries (ISO 3166)",
        "ISDA Equity Taxonomy",
        "ISO10383_MIC.xlsx",
        "SHA-256 9d0d3320cb2a",
    ):
        contains(area, f"left rail shows {needle}", needle, rail)
    page.select_option("#fLoaded", "true")
    wait_text(page, "#refRowCount", "13 venues loaded in CASM")
    record(
        area,
        "the loaded venues can be narrowed to",
        "13",
        str(page.locator("#refTable tbody tr").count()),
    )
    table = page.inner_text("#refTable")
    for mic in (
        "XNAS",
        "XNYS",
        "XASE",
        "ARCX",
        "BATS",
        "EDGX",
        "IEXG",
        "XCBO",
        "XCME",
        "XCBT",
        "IFUS",
        "XOFF",
        "XXXX",
    ):
        contains(area, f"venue {mic} listed", mic, table)
    page.click("#refTable tr[data-key=XNAS]")
    wait_text(page, "#refInspector h2", "NASDAQ - ALL MARKETS")
    detail = page.inner_text("#refInspector")
    for needle in (
        "549300L8X1Q78ERXFD06",
        "249 of 398 instruments listed here",
        "EXCHANGE",
    ):
        contains(area, f"XNAS detail shows {needle}", needle, detail)
    shot(page, "07-reference-venues")
    page.select_option("#fLoaded", "false")
    wait_text(page, "#refRowCount", "2,883 venues in the ISO 10383 registry")

    for set_id, pager, needle, shot_name in (
        ("gics", "262 rows", "Energy Equipment & Services", "08-reference-gics"),
        ("taxonomy", "17 rows", "EQ-SPT-COMMON", "09-reference-taxonomy"),
        ("countries", "249 rows", "Cayman Islands", "10-reference-countries"),
        ("isda", "34 rows", "Price Return Basic Performance", "11-reference-isda"),
    ):
        page.goto(f"{UI}/#/reference/{set_id}")
        wait_text(page, "#refRowCount", pager)
        contains(area, f"{set_id} row count", pager, page.inner_text("#refRowCount"))
        page.fill("#refSearch", needle.split()[0])
        time.sleep(0.6)
        contains(
            area, f"{set_id} search finds {needle}", needle, page.inner_text("#refTable")
        )
        page.fill("#refSearch", "")
        wait_text(page, "#refRowCount", pager)
        grid = " | ".join(page.locator("#refTable thead th").all_inner_texts())
        for column in GRID_COLUMNS.get(set_id, ()):
            contains(area, f"{set_id} grid column {column}", column, grid)
        no_pagination(page, area)
        shot(page, shot_name)
    page.goto(f"{UI}/#/reference/taxonomy")
    page.wait_for_selector("#refTable tr[data-key=EQ-SPT-COMMON]", timeout=WAIT_MS)
    row = page.inner_text("#refTable tr[data-key=EQ-SPT-COMMON]")
    for needle in (
        "EQ-SPT-COMMON",
        "EQ",
        "Equity",
        "SPT",
        "Spot",
        "Ordinary common shares",
        "CASM",
    ):
        contains(area, f"taxonomy row shows {needle}", needle, row)
    page.click("#refTable tr[data-key=EQ-SPT-COMMON]")
    wait_text(
        page, "#refInspector h2", "EQ-SPT-COMMON"
    )  # the click has replaced the first row's inspector
    wait_text(page, "#refInspector", "Instruments with this code")
    contains(
        area,
        "taxonomy inspector: EQ-SPT-COMMON has 201 instruments",
        "201",
        page.inner_text("#refInspector"),
    )
    page.goto(f"{UI}/#/reference/gics")
    page.wait_for_selector("#refTable tr[data-key='10101010']", timeout=WAIT_MS)
    expected_rows = {
        "10": ("Sector", "10", "Energy"),
        "1010": ("Industry Group", "1010", "Energy", "10"),
        "101010": ("Industry", "101010", "Energy Equipment & Services", "1010"),
        "10101010": (
            "Sub-Industry",
            "10101010",
            "Oil & Gas Drilling",
            "101010",
            "Energy Equipment & Services",
        ),
    }
    for key, needles in expected_rows.items():
        row_text = page.inner_text(f"#refTable tr[data-key='{key}']")
        for needle in needles:
            contains(
                area, f"GICS {needles[0]} row {key} shows {needle}", needle, row_text
            )
    for level, count in (
        ("Sector", "11"),
        ("Industry Group", "24"),
        ("Industry", "69"),
        ("Sub-Industry", "158"),
    ):
        page.select_option("#fLevel", level)
        wait_text(page, "#refRowCount", f"{count} rows")
        record(
            area,
            f"GICS level filter {level}",
            count,
            str(page.locator("#refTable tbody tr").count()),
        )
    page.select_option("#fLevel", "")
    wait_text(page, "#refRowCount", "262 rows")
    page.click("#refTable tr[data-key='10101010']")
    wait_text(page, "#refInspector h2", "Oil & Gas Drilling")
    gics_detail = page.inner_text("#refInspector")
    for needle in (
        "Sector",
        "Industry Group",
        "Industry",
        "Sub-Industry",
        "Energy Equipment & Services",
        "Drilling contractors",
    ):
        contains(area, f"GICS inspector shows {needle}", needle, gics_detail)
    page.click("#refTable tr[data-key='10']")
    wait_text(page, "#refInspector h2", "Energy")
    wait_text(page, "#refInspector", "Industry Groups (1)")
    shot(page, "08b-reference-gics-sector")


def validate_wiki(page: Page) -> None:
    area = "Wiki"
    pages = api_json("/api/v1/wiki")
    ids = [p["id"] for p in pages]
    record(
        area,
        "reading order from the API",
        "index first, then sorted",
        "ok" if ids[0] == "index" and ids[1:] == sorted(ids[1:]) else str(ids),
        ids[0] == "index" and ids[1:] == sorted(ids[1:]),
    )
    for needed in (
        "1_1-sec-master-ops-flow",
        "1_3-project-scope",
        "3_1-database-schema",
        "3_2-tech-stack",
        "3_3-api-ui",
    ):
        record(area, f"page {needed} listed", "True", str(needed in ids))
    page.goto(f"{UI}/#/wiki/index")
    page.wait_for_selector("#wikiArticle h1", timeout=WAIT_MS)
    rail = [t.strip() for t in page.locator("aside nav a").all_inner_texts()]
    record(
        area,
        "left rail matches API order and titles",
        " | ".join(p["title"] for p in pages),
        " | ".join(rail),
    )
    contains(
        area,
        "index page has the known gaps",
        "Known gaps",
        page.inner_text("#wikiArticle"),
    )
    shot(page, "12-wiki-index")
    page.goto(f"{UI}/#/wiki/1_3-project-scope")
    page.wait_for_selector("#wikiArticle h1", timeout=WAIT_MS)
    page.wait_for_selector("#wikiArticle .mermaid svg", timeout=WAIT_MS)
    wait_diagrams_drawn(page)
    diagrams = page.locator("#wikiArticle .mermaid svg").count()
    record(
        area,
        "plan page draws its Mermaid diagram",
        ">= 1 SVG",
        f"{diagrams} SVG",
        diagrams >= 1,
    )
    tables = page.locator("#wikiArticle table").count()
    record(area, "plan page renders markdown tables", ">= 5", str(tables), tables >= 5)
    raw_fences = page.locator("#wikiArticle pre code.language-mermaid").count()
    record(area, "no raw mermaid code left", "0", str(raw_fences))
    shot(page, "13-wiki-plan-mermaid")
    page.click("#wikiArticle a[href^='#/wiki/']")
    page.wait_for_function("() => location.hash.startsWith('#/wiki/')")
    md_links = page.locator("#wikiArticle a[href$='.md']").count()
    record(area, "no unresolved .md links on the page reached", "0", str(md_links))
    for page_id in ("3_1-database-schema", "3_2-tech-stack", "3_3-api-ui"):
        page.goto(f"{UI}/#/wiki/{page_id}")
        page.wait_for_selector("#wikiArticle h1", timeout=WAIT_MS)
        record(
            area,
            f"{page_id} renders a heading",
            "True",
            str(page.locator("#wikiArticle h1").count() >= 1),
        )
    page.goto(f"{UI}/#/wiki/index")  # the README has a fenced quick-start block
    page.wait_for_selector("#wikiArticle pre", timeout=WAIT_MS)
    record(
        area,
        "code blocks have a white background",
        "rgb(255, 255, 255)",
        computed(page, "#wikiArticle pre", "backgroundColor"),
    )
    dark_text = computed(page, "#wikiArticle pre code", "color")
    channels = [int(v) for v in dark_text.strip("rgba() ").split(",")[:3]]
    record(
        area,
        "code block text is dark",
        "r, g, b all < 80",
        dark_text,
        all(c < 80 for c in channels),
    )
    shot(page, "14b-wiki-code-block")
    shot(page, "14-wiki-database")


def computed(page: Page, selector: str, prop: str) -> str:
    return page.eval_on_selector(selector, "(el, p) => getComputedStyle(el)[p]", prop)


def box(page: Page, selector: str) -> dict[str, float]:
    return page.eval_on_selector(
        selector,
        "el => { const r = el.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, height: r.height}; }",
    )


def validate_consistency(page: Page) -> None:
    """The same type, row height and docked-inspector layout on every screen, with the page filled top to bottom."""
    area = "Consistency"
    viewport = 1000
    page.goto(f"{UI}/#/securities")
    page.wait_for_selector("#tableArea tbody tr[data-id]", timeout=WAIT_MS)
    wait_text(page, "#rowCount", "398 securities")
    seen = {
        "cell size": computed(page, "#tableArea tbody tr td", "fontSize"),
        "cell family": computed(page, "#tableArea tbody tr td", "fontFamily"),
        "title size": computed(page, "h1", "fontSize"),
        "row height": str(box(page, "#tableArea tbody tr")["height"]),
        "head height": str(box(page, "#tableArea thead tr")["height"]),
    }
    page.fill("#searchInput", "55306NAB0")
    wait_text(page, "#rowCount", "1 security")
    wait_text(page, "#inspector", "MKS INC 1.25 06/01/2030")
    time.sleep(0.5)
    inspector_bottom = box(page, "#inspector")["bottom"]
    pager_bottom = box(page, "#rowCount")["bottom"]
    record(
        area,
        "Securities inspector reaches the bottom of the window",
        f">= {viewport * 0.98:.0f}px",
        f"{inspector_bottom:.0f}px",
        inspector_bottom >= viewport * 0.98,
    )
    record(
        area,
        "Securities pager sits at the bottom with a single result",
        f">= {viewport * 0.9:.0f}px",
        f"{pager_bottom:.0f}px",
        pager_bottom >= viewport * 0.9,
    )
    shot(page, "15-securities-single-result-full-height")

    page.goto(f"{UI}/#/reference/taxonomy")
    page.wait_for_selector("#refTable tbody tr", timeout=WAIT_MS)
    wait_text(page, "#refRowCount", "17 rows")
    time.sleep(0.5)
    reference = {
        "cell size": computed(page, "#refTable tbody tr td", "fontSize"),
        "cell family": computed(page, "#refTable tbody tr td", "fontFamily"),
        "title size": computed(page, "h1", "fontSize"),
        "row height": str(box(page, "#refTable tbody tr")["height"]),
        "head height": str(box(page, "#refTable thead tr")["height"]),
    }
    for key, value in seen.items():
        record(area, f"Securities and Reference agree on {key}", value, reference[key])
    ref_inspector = box(page, "#refInspector")["height"]
    ref_pager = box(page, "#refRowCount")["bottom"]
    record(
        area,
        "Reference inspector is full height",
        f">= {viewport * 0.9:.0f}px",
        f"{ref_inspector:.0f}px",
        ref_inspector >= viewport * 0.9,
    )
    record(
        area,
        "Reference pager sits at the bottom of a short table",
        f">= {viewport * 0.9:.0f}px",
        f"{ref_pager:.0f}px",
        ref_pager >= viewport * 0.9,
    )
    shot(page, "16-reference-short-table-full-height")

    page.goto(f"{UI}/#/wiki/3_1-database-schema")
    page.wait_for_selector("#wikiArticle p", timeout=WAIT_MS)
    record(
        area,
        "Wiki body text uses the same font family",
        seen["cell family"],
        computed(page, "#wikiArticle p", "fontFamily"),
    )
    record(
        area,
        "Wiki body text uses the same font size",
        seen["cell size"],
        computed(page, "#wikiArticle p", "fontSize"),
    )
    record(
        area,
        "Wiki code uses the same monospace family as the tables",
        computed(page, "#wikiArticle code", "fontFamily"),
        computed(page, "#wikiArticle code", "fontFamily"),
    )
    page.goto(f"{UI}/#/securities")
    page.wait_for_selector("#tableArea tbody tr[data-id]", timeout=WAIT_MS)
    mono = computed(page, "#tableArea tbody tr td:nth-child(5)", "fontFamily")
    page.goto(f"{UI}/#/wiki/3_1-database-schema")
    page.wait_for_selector("#wikiArticle code", timeout=WAIT_MS)
    record(
        area,
        "Wiki code and table identifiers share one monospace family",
        mono,
        computed(page, "#wikiArticle code", "fontFamily"),
    )


def write_report(started: str) -> None:
    passed: int = sum(1 for r in results if r[4])
    lines: list[str] = [
        "# UI validation report",
        "",
        f"Run: {started} UTC. Result: **{passed} of {len(results)} checks passed**; "
        f"{len(console_errors)} console errors, {len(failed_requests)} failed requests.",
        "",
        "## Tools used",
        "",
        "- `src/main.py`: launched the API (9099) and UI (9095); the API rebuilt the database first",
        '- Playwright driving the installed Google Chrome (`channel="chrome"`) over the Chrome DevTools Protocol: navigation, DOM reads, screenshots, console and network listeners',
        "- urllib: direct API calls to compare with the screen",
        "- Skill: `.claude/skills/validate-ui` (script `validate_ui.py`)",
        "",
        "## Checks",
        "",
        "| Area | Check | Expected | Seen | Result |",
        "|---|---|---|---|---|",
    ]
    for area, check, expected, seen, ok in results:
        cells = [area, check, expected, seen]
        lines.append(
            "| "
            + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells)
            + f" | {'pass' if ok else '**FAIL**'} |"
        )
    lines += ["", "## Browser console errors", ""] + (
        [f"- {e}" for e in console_errors] or ["None."]
    )
    lines += ["", "## Failed requests", ""] + (
        [f"- {e}" for e in failed_requests] or ["None."]
    )
    lines += ["", "## Screenshots", ""] + [
        f"- `screenshots/{p.name}`" for p in sorted(SHOTS.glob("*.png"))
    ]
    (OUT / "ui-validation-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()
    started: str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    print("Starting the app...")
    proc = start_app()
    try:
        validate_api()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.on(
                "console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None,
            )
            page.on(
                "requestfailed",
                lambda r: (
                    failed_requests.append(f"{r.url} ({r.failure})")
                    if "favicon" not in r.url
                    else None
                ),
            )
            page.on(
                "response",
                lambda r: (
                    failed_requests.append(f"{r.url} -> {r.status}")
                    if r.status >= 400 and "favicon" not in r.url
                    else None
                ),
            )
            for name, step in (
                ("securities", validate_securities),
                ("reference", validate_reference),
                ("wiki", validate_wiki),
                ("consistency", validate_consistency),
            ):
                print(f"Validating {name}...")
                try:
                    step(page)
                except Exception as error:  # a step that cannot finish is a failed check
                    record(
                        name,
                        "step completed",
                        "no error",
                        f"{type(error).__name__}: {str(error)[:200]}",
                        False,
                    )
                    shot(page, f"error-{name}")
            record("Browser", "console errors", "0", str(len(console_errors)))
            record("Browser", "failed requests", "0", str(len(failed_requests)))
            browser.close()
    finally:
        stop_pid(
            pid=proc.pid
        )  # the whole process tree: on Windows the launcher has a child that holds the ports
        free_ports(host="127.0.0.1", ports=[9099, 9095])
    write_report(started)
    failed = [r for r in results if not r[4]]
    print(
        f"\n{len(results) - len(failed)} of {len(results)} checks passed. Report: {OUT / 'ui-validation-report.md'}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
