"""SQL for the Securities Universe screen. Returns rows; decides nothing."""

from casm.api.utils.database_utils import Connection, Row, fetch_all, fetch_one, scalar
from casm.api.utils.sql_utils import ESCAPE_CLAUSE, contains, prefix
from casm.api.v1.models import ExceptionSearch, IssuerSearch, SecuritySearch

SORT_COLUMNS: dict[str, str] = {
    "name": "i.security_name",
    "product_code": "i.product_code",
    "ticker": "l.symbol",
    "mic": "l.mic",
    "cusip": "cusip.value",
    "figi": "figi.value",
    "country": "s.country_code",
    "confidence": "l.confidence",
    "underlying": "u.security_name",
    "bbg_ticker": "l.bbg_ticker",
    "composite_figi": "l.composite_figi",
    "cik": "s.cik",
}
# Scopes no source fills, so a search by them can only find nothing
ISSUER_SORT_COLUMNS: dict[str, str] = {
    "name": "s.legal_name",
    "type": "s.issuer_type",
    "country": "s.country_code",
    "cik": "s.cik",
    "instruments": "instruments",
}
NOT_HELD_SCOPES: frozenset[str] = frozenset({"isin", "sedol"})
SUBTYPE_TABLES: frozenset[str] = frozenset(
    {
        "sec_instrument_eq_spt",
        "sec_instrument_eq_warrant_right",
        "sec_instrument_fi_bond",
        "sec_instrument_fnd",
        "sec_instrument_fut_contract",
        "sec_instrument_opt_series",
        "sec_instrument_fwd_contract",
        "sec_instrument_swp_contract",
    }
)
FROM_INSTRUMENTS: str = """
    FROM sec_instrument i
    JOIN sec_issuer s USING (issuer_id)
    LEFT JOIN sec_listing l ON l.instrument_id = i.instrument_id AND l.primary_marker = 1
    LEFT JOIN sec_identifier_xref cusip ON cusip.instrument_id = i.instrument_id AND cusip.scheme = 'CUSIP'
    LEFT JOIN sec_identifier_xref figi ON figi.instrument_id = i.instrument_id AND figi.scheme = 'FIGI'
"""
CUSIP_OF_INSTRUMENT: str = (
    "(SELECT value FROM sec_identifier_xref x WHERE x.instrument_id = i.instrument_id AND x.scheme = 'CUSIP')"
)


def search_clause(*, q: str, scope: str) -> tuple[str, list[object]]:
    """The WHERE fragment and parameters for a search string within a scope."""
    starts: str = prefix(text=q)
    has: str = contains(text=q)
    esc: str = ESCAPE_CLAUSE
    if scope in NOT_HELD_SCOPES:
        return "FALSE", []
    if scope == "cusip":
        return f"cusip.value ILIKE ? {esc}", [starts]
    if scope == "figi":
        return f"(figi.value ILIKE ? {esc} OR l.composite_figi ILIKE ? {esc})", [
            starts,
            starts,
        ]
    if scope == "ticker":
        return f"(l.symbol ILIKE ? {esc} OR l.bbg_ticker ILIKE ? {esc})", [starts, starts]
    if scope == "name":
        return f"(i.security_name ILIKE ? {esc} OR s.legal_name ILIKE ? {esc})", [
            has,
            has,
        ]
    clause: str = (
        f"(i.security_name ILIKE ? {esc} OR s.legal_name ILIKE ? {esc} OR cusip.value ILIKE ? {esc} "
        f"OR figi.value ILIKE ? {esc} OR l.symbol ILIKE ? {esc} OR l.bbg_ticker ILIKE ? {esc})"
    )
    return clause, [has, has, starts, starts, starts, starts]


def where_for(*, search: SecuritySearch) -> tuple[str, list[object]]:
    """The full WHERE clause for a search, with its parameters."""
    where: list[str] = []
    params: list[object] = []
    if search.q and search.q.strip():
        clause, clause_params = search_clause(q=search.q.strip(), scope=search.scope)
        where.append(clause)
        params.extend(clause_params)
    if search.product_code:
        where.append("i.product_code = ?")
        params.append(search.product_code)
    if search.mic:
        where.append("l.mic = ?")
        params.append(search.mic.upper())
    return (("WHERE " + " AND ".join(where)) if where else ""), params


def underlying_links_sql() -> str:
    """A CTE of (instrument_id, underlying_instrument_id) over every subtype table that has an underlying."""
    union: str = " UNION ALL ".join(
        f"SELECT instrument_id, underlying_instrument_id FROM {table} WHERE underlying_instrument_id IS NOT NULL"
        for table in UNDERLYING_TABLES
    )
    return f"WITH links AS ({union})"


def find_instruments(*, con: Connection, search: SecuritySearch) -> list[Row]:
    """Every matching instrument with its global identifiers (CUSIP, FIGI, composite FIGI, Bloomberg
    ticker, issuer CIK), primary listing and underlying security."""
    where_sql, params = where_for(search=search)
    return fetch_all(
        con=con,
        sql=f"""
            {underlying_links_sql()}
            SELECT i.instrument_id, i.security_name AS name, i.product_code, l.symbol AS ticker,
                   l.bbg_ticker, l.mic, l.confidence, cusip.value AS cusip, figi.value AS figi,
                   l.composite_figi, s.cik, s.country_code AS country, s.legal_name AS issuer,
                   u.security_name AS underlying_name
            {FROM_INSTRUMENTS}
            LEFT JOIN links lk ON lk.instrument_id = i.instrument_id
            LEFT JOIN sec_instrument u ON u.instrument_id = lk.underlying_instrument_id
            {where_sql}
            ORDER BY {SORT_COLUMNS[search.sort]} {search.direction.upper()} NULLS LAST, i.instrument_id
            """,
        params=params,
    )


def product_code_counts(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT p.code, p.description, count(i.instrument_id) AS count
               FROM ref_product_code p LEFT JOIN sec_instrument i ON i.product_code = p.code
               GROUP BY p.code, p.description HAVING count(i.instrument_id) > 0 ORDER BY p.code""",
    )


def primary_venue_counts(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT l.mic, v.name, count(*) AS count FROM sec_listing l
               JOIN ref_venue v USING (mic) WHERE l.primary_marker = 1
               GROUP BY l.mic, v.name ORDER BY count(*) DESC""",
    )


def universe_totals(*, con: Connection) -> Row:
    return {
        "instruments": scalar(con=con, sql="SELECT count(*) FROM sec_instrument"),
        "exceptions": scalar(con=con, sql="SELECT count(*) FROM sec_exception_queue"),
    }


def find_exceptions(*, con: Connection, search: ExceptionSearch) -> list[Row]:
    where: str = "WHERE reason_code = ?" if search.reason else ""
    params: list[object] = [search.reason] if search.reason else []
    return fetch_all(
        con=con,
        sql=f"""SELECT exception_id, row_number, name_of_issuer, title_of_class, cusip, reason_code, detail
                FROM sec_exception_queue {where} ORDER BY row_number""",
        params=params,
    )


def exception_reasons(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="SELECT reason_code, count(*) AS count FROM sec_exception_queue GROUP BY 1 ORDER BY 2 DESC",
    )


def instrument_head(*, con: Connection, instrument_id: int) -> Row | None:
    """The instrument with its taxonomy row, asset class and base product."""
    return fetch_one(
        con=con,
        sql="""SELECT i.instrument_id, i.security_name AS name, i.product_code, i.source, i.as_of,
                      i.is_synthetic, i.issuer_id, p.description, p.source AS taxonomy_source,
                      p.subtype_table, p.desk_family, p.cftc_asset_class, p.mifid_category, p.isda_path,
                      ac.code AS asset_class_code, ac.name AS asset_class_name,
                      bp.code AS base_product_code, bp.name AS base_product_name
               FROM sec_instrument i
               JOIN ref_product_code p ON p.code = i.product_code
               JOIN ref_asset_class ac ON ac.code = p.asset_class_code
               JOIN ref_base_product bp ON bp.code = p.base_product
               WHERE i.instrument_id = ?""",
        params=[instrument_id],
    )


def issuer_of(*, con: Connection, issuer_id: object) -> Row | None:
    return fetch_one(
        con=con,
        sql="""SELECT s.issuer_id, s.legal_name, s.issuer_type, s.country_code, c.name AS country_name,
                      s.cusip6, s.cik, s.lei, s.sic, s.gics_code, s.source, s.as_of
               FROM sec_issuer s LEFT JOIN ref_country c ON c.alpha2 = s.country_code
               WHERE s.issuer_id = ?""",
        params=[issuer_id],
    )


def identifiers_of(*, con: Connection, instrument_id: int) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT scheme, value, source, as_of FROM sec_identifier_xref
               WHERE instrument_id = ? ORDER BY scheme""",
        params=[instrument_id],
    )


def listings_of(*, con: Connection, instrument_id: int) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT l.mic, v.name AS venue_name, v.venue_type, l.symbol, l.bbg_ticker, l.figi,
                      l.composite_figi, l.lot_size, l.currency, l.primary_marker IS NOT NULL AS is_primary,
                      l.source, l.as_of, l.confidence, v.venue_type IN ('OTC', 'NONE') AS is_otc
               FROM sec_listing l JOIN ref_venue v USING (mic)
               WHERE l.instrument_id = ? ORDER BY is_primary DESC, l.mic""",
        params=[instrument_id],
    )


def subtype_row(*, con: Connection, table: str, instrument_id: int) -> Row | None:
    """The instrument's row in its subtype table; `table` must be a known subtype table."""
    if table not in SUBTYPE_TABLES:
        return None
    return fetch_one(
        con=con,
        sql=f"SELECT * FROM {table} WHERE instrument_id = ?",
        params=[instrument_id],
    )


# Subtype tables whose rows point at an underlying instrument
UNDERLYING_TABLES: tuple[str, ...] = (
    "sec_instrument_eq_warrant_right",
    "sec_instrument_fi_bond",
    "sec_instrument_fut_contract",
    "sec_instrument_opt_series",
    "sec_instrument_fwd_contract",
    "sec_instrument_swp_contract",
)


def instrument_summary(*, con: Connection, instrument_id: object) -> Row | None:
    """An instrument's name, product code, primary listing and CUSIP, for a link from another instrument."""
    return fetch_one(
        con=con,
        sql=f"""SELECT i.instrument_id, i.security_name AS name, i.product_code, l.symbol AS ticker, l.mic,
                       {CUSIP_OF_INSTRUMENT} AS cusip
                FROM sec_instrument i
                LEFT JOIN sec_listing l ON l.instrument_id = i.instrument_id AND l.primary_marker = 1
                WHERE i.instrument_id = ?""",
        params=[instrument_id],
    )


def find_issuers(*, con: Connection, search: IssuerSearch) -> list[Row]:
    """Every issuer matching the search, with how many instruments it has."""
    esc: str = ESCAPE_CLAUSE
    where: str = ""
    params: list[object] = []
    if search.q and search.q.strip():
        where = f"WHERE (s.legal_name ILIKE ? {esc} OR s.cik ILIKE ? {esc} OR s.cusip6 ILIKE ? {esc})"
        params = [
            contains(text=search.q.strip()),
            prefix(text=search.q.strip()),
            prefix(text=search.q.strip()),
        ]
    return fetch_all(
        con=con,
        sql=f"""
            SELECT s.issuer_id, s.legal_name, s.issuer_type, s.country_code AS country, c.name AS country_name,
                   s.cik, s.sic, s.cusip6,
                   (SELECT count(*) FROM sec_instrument i WHERE i.issuer_id = s.issuer_id) AS instruments
            FROM sec_issuer s LEFT JOIN ref_country c ON c.alpha2 = s.country_code
            {where}
            ORDER BY {ISSUER_SORT_COLUMNS[search.sort]} {search.direction.upper()} NULLS LAST, s.issuer_id
            """,
        params=params,
    )


def issuer_instruments(*, con: Connection, issuer_id: int) -> list[Row]:
    """The instruments of one issuer with their primary listing and CUSIP."""
    return fetch_all(
        con=con,
        sql=f"""SELECT i.instrument_id, i.security_name AS name, i.product_code, l.symbol AS ticker, l.mic,
                       {CUSIP_OF_INSTRUMENT} AS cusip
                FROM sec_instrument i
                LEFT JOIN sec_listing l ON l.instrument_id = i.instrument_id AND l.primary_marker = 1
                WHERE i.issuer_id = ? ORDER BY i.product_code, i.security_name""",
        params=[issuer_id],
    )
