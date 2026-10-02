"""SQL for the Reference Data screen. Returns rows; decides nothing."""

from casm.api.utils.database_utils import Connection, Row, fetch_all, fetch_one, scalar
from casm.api.utils.sql_utils import ESCAPE_CLAUSE, contains
from casm.api.v1.models import VenueSearch

VENUE_SORT: dict[str, str] = {
    "mic": "r.mic",
    "operating_mic": "r.operating_mic",
    "name": "r.market_name",
    "country": "country",
    "type": "v.venue_type",
    "status": "r.status",
    "listings": "listings",
}
VENUES_FROM: str = """
    FROM ref_mic_registry r
    LEFT JOIN ref_venue v USING (mic)
    LEFT JOIN (SELECT mic, count(*) AS n FROM sec_listing GROUP BY mic) c USING (mic)
"""
CUSIP_OF_INSTRUMENT: str = (
    "(SELECT value FROM sec_identifier_xref x WHERE x.instrument_id = i.instrument_id AND x.scheme = 'CUSIP')"
)


def set_counts(*, con: Connection) -> dict[str, int]:
    """Row counts of each reference set, plus the full MIC registry."""
    return {
        "venues": scalar(con=con, sql="SELECT count(*) FROM ref_venue"),
        "registry": scalar(con=con, sql="SELECT count(*) FROM ref_mic_registry"),
        "gics": scalar(con=con, sql="SELECT count(*) FROM ref_gics"),
        "taxonomy": scalar(con=con, sql="SELECT count(*) FROM ref_product_code"),
        "countries": scalar(con=con, sql="SELECT count(*) FROM ref_country"),
        "isda": scalar(con=con, sql="SELECT count(*) FROM ref_isda_equity_taxonomy"),
    }


def venue_where(*, search: VenueSearch) -> tuple[str, list[object]]:
    where: list[str] = []
    params: list[object] = []
    if search.loaded or search.venue_type:
        where.append("v.mic IS NOT NULL")
    if search.q and search.q.strip():
        esc: str = ESCAPE_CLAUSE
        where.append(
            f"(r.mic ILIKE ? {esc} OR r.market_name ILIKE ? {esc} OR r.operating_mic ILIKE ? {esc})"
        )
        params.extend([contains(text=search.q.strip())] * 3)
    if search.country:
        where.append("coalesce(v.country, r.country) = ?")
        params.append(search.country.upper())
    if search.venue_type:
        where.append("v.venue_type = ?")
        params.append(search.venue_type)
    if search.status:
        where.append("r.status = ?")
        params.append(search.status)
    return (("WHERE " + " AND ".join(where)) if where else ""), params


def find_venues(*, con: Connection, search: VenueSearch) -> list[Row]:
    where_sql, params = venue_where(search=search)
    return fetch_all(
        con=con,
        sql=f"""SELECT r.mic, r.operating_mic, r.market_name AS name, coalesce(v.country, r.country) AS country,
                       v.venue_type, r.status, coalesce(c.n, 0) AS listings, v.mic IS NOT NULL AS loaded
                {VENUES_FROM} {where_sql}
                ORDER BY {VENUE_SORT[search.sort]} {search.direction.upper()} NULLS LAST, r.mic""",
        params=params,
    )


def venue_facets(*, con: Connection, loaded: bool) -> dict[str, list[object]]:
    """The countries, venue types and statuses available to the venue filters."""
    scope: str = "WHERE v.mic IS NOT NULL" if loaded else ""
    countries: list[Row] = fetch_all(
        con=con,
        sql=f"SELECT DISTINCT coalesce(v.country, r.country) AS value {VENUES_FROM} {scope} ORDER BY 1",
    )
    types: list[Row] = fetch_all(
        con=con, sql="SELECT DISTINCT venue_type AS value FROM ref_venue ORDER BY 1"
    )
    statuses: list[Row] = fetch_all(
        con=con, sql=f"SELECT DISTINCT r.status AS value {VENUES_FROM} {scope} ORDER BY 1"
    )
    return {
        "countries": [row["value"] for row in countries if row["value"]],
        "types": [row["value"] for row in types],
        "statuses": [row["value"] for row in statuses],
    }


def registry_record(*, con: Connection, mic: str) -> Row | None:
    return fetch_one(
        con=con,
        sql="""SELECT r.mic, r.operating_mic, r.oprt_sgmt, r.market_name, r.lei, r.market_category_code,
                      r.country, r.status, o.market_name AS operating_name
               FROM ref_mic_registry r JOIN ref_mic_registry o ON o.mic = r.operating_mic
               WHERE r.mic = ?""",
        params=[mic],
    )


def loaded_venue(*, con: Connection, mic: str) -> Row | None:
    return fetch_one(
        con=con,
        sql="""SELECT v.venue_type, v.country, c.name AS country_name, v.venue_type IN ('OTC', 'NONE') AS is_otc
               FROM ref_venue v LEFT JOIN ref_country c ON c.alpha2 = v.country WHERE v.mic = ?""",
        params=[mic],
    )


def venue_usage(*, con: Connection, mic: str) -> Row:
    """How many listings sit on a venue, how many are primary, and the split by product code."""
    counts: Row | None = fetch_one(
        con=con,
        sql="SELECT count(*) AS listings, count(primary_marker) AS primary_listings FROM sec_listing WHERE mic = ?",
        params=[mic],
    )
    return {
        **(counts or {}),
        "total_instruments": scalar(con=con, sql="SELECT count(*) FROM sec_instrument"),
        "by_product": fetch_all(
            con=con,
            sql="""SELECT i.product_code, count(*) AS count FROM sec_listing l
                   JOIN sec_instrument i USING (instrument_id) WHERE l.mic = ?
                   GROUP BY 1 ORDER BY 2 DESC, 1""",
            params=[mic],
        ),
    }


def venue_assets(*, con: Connection, mic: str) -> list[Row]:
    return fetch_all(
        con=con,
        sql=f"""SELECT i.instrument_id, i.security_name AS name, i.product_code, l.symbol AS ticker,
                       l.confidence, {CUSIP_OF_INSTRUMENT} AS cusip
                FROM sec_listing l JOIN sec_instrument i USING (instrument_id)
                WHERE l.mic = ? ORDER BY i.security_name""",
        params=[mic],
    )


def gics_levels(*, con: Connection) -> Row | None:
    return fetch_one(
        con=con,
        sql="""SELECT count(DISTINCT sector_code) AS sectors, count(DISTINCT industry_group_code) AS groups,
                      count(DISTINCT industry_code) AS industries, count(*) AS sub_industries FROM ref_gics""",
    )


def gics_rows(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT g.*, (SELECT count(*) FROM sec_issuer s WHERE s.gics_code = g.sub_industry_code) AS issuers
               FROM ref_gics g ORDER BY sub_industry_code""",
    )


def taxonomy_rows(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT p.code, p.description, p.source, p.subtype_table, p.desk_family, p.cftc_asset_class,
                      p.mifid_category, p.isda_path, ac.code AS asset_class_code, ac.name AS asset_class_name,
                      bp.code AS base_product_code, bp.name AS base_product_name,
                      (SELECT count(*) FROM sec_instrument i WHERE i.product_code = p.code) AS instruments
               FROM ref_product_code p
               JOIN ref_asset_class ac ON ac.code = p.asset_class_code
               JOIN ref_base_product bp ON bp.code = p.base_product
               ORDER BY p.code""",
    )


def product_code_exists(*, con: Connection, code: str) -> bool:
    return (
        scalar(
            con=con,
            sql="SELECT count(*) FROM ref_product_code WHERE code = ?",
            params=[code],
        )
        > 0
    )


def instruments_with_product(*, con: Connection, code: str) -> list[Row]:
    return fetch_all(
        con=con,
        sql=f"""SELECT i.instrument_id, i.security_name AS name, l.symbol AS ticker, l.mic,
                       {CUSIP_OF_INSTRUMENT} AS cusip
                FROM sec_instrument i
                LEFT JOIN sec_listing l ON l.instrument_id = i.instrument_id AND l.primary_marker = 1
                WHERE i.product_code = ? ORDER BY i.security_name""",
        params=[code],
    )


def country_rows(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT c.alpha2, c.name,
                      (SELECT count(*) FROM sec_issuer s WHERE s.country_code = c.alpha2) AS issuers,
                      (SELECT count(*) FROM ref_venue v WHERE v.country = c.alpha2) AS venues
               FROM ref_country c ORDER BY c.name""",
    )


def country_exists(*, con: Connection, alpha2: str) -> bool:
    return (
        scalar(
            con=con,
            sql="SELECT count(*) FROM ref_country WHERE alpha2 = ?",
            params=[alpha2],
        )
        > 0
    )


def issuers_in_country(*, con: Connection, alpha2: str) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT s.issuer_id, s.legal_name, s.issuer_type, s.cik, s.sic,
                      (SELECT count(*) FROM sec_instrument i WHERE i.issuer_id = s.issuer_id) AS instruments
               FROM sec_issuer s WHERE s.country_code = ? ORDER BY s.legal_name""",
        params=[alpha2],
    )


def isda_rows(*, con: Connection) -> list[Row]:
    return fetch_all(
        con=con,
        sql="""SELECT isda_row_no, base_product, sub_product, transaction_type
               FROM ref_isda_equity_taxonomy ORDER BY isda_row_no""",
    )
