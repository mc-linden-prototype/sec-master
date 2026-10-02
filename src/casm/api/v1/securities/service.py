"""Business logic for the Securities Universe: identifier detection, filters and the instrument detail.

The detail is assembled from several queries and adds what the database cannot say by itself: which
attributes are not held, which integrity rules the instrument satisfies, and where each datapoint came from.
"""

import logging
import re

from casm.api.errors import NotFoundError
from casm.api.utils.database_utils import Connection, Row
from casm.api.v1.models import ExceptionSearch, IssuerSearch, SecuritySearch
from casm.api.v1.securities import queries

logger: logging.Logger = logging.getLogger(__name__)
UNDERLYING_REQUIRED: frozenset[str] = frozenset(
    {"FI-BND-CONV", "EQ-SPT-WARRANT", "EQ-SPT-RIGHTS"}
)
DROPPED_TERM_KEYS: tuple[str, ...] = (
    "instrument_id",
    "product_code",
    "underlying_instrument_id",
    "underlying_product_code",
)


def detect_identifier(*, text: str) -> str | None:
    """Name the identifier a search string looks like (FIGI, ISIN, CUSIP or SEDOL), if any."""
    value: str = text.strip().upper()
    if re.fullmatch(r"BBG[A-Z0-9]{9}", value):
        return "FIGI"
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value):
        return "ISIN"
    if re.fullmatch(r"[0-9A-Z*@#]{8}[0-9]", value):
        return "CUSIP"
    if re.fullmatch(r"[0-9BCDFGHJKLMNPQRSTVWXYZ]{6}[0-9]", value):
        return "SEDOL"
    return None


def search_securities(*, con: Connection, search: SecuritySearch) -> dict[str, object]:
    """Every matching instrument, the total, the identifier type the query looks like, and a note."""
    query: str = (search.q or "").strip()
    note: str | None = None
    if query and search.scope in queries.NOT_HELD_SCOPES:
        note = f"No {search.scope.upper()} is held in this prototype (no free authoritative source)."
    items: list[Row] = queries.find_instruments(con=con, search=search)
    logger.debug(
        "securities search q=%r scope=%s product_code=%s mic=%s sort=%s %s -> %d rows",
        query,
        search.scope,
        search.product_code,
        search.mic,
        search.sort,
        search.direction,
        len(items),
    )
    return {
        "total": len(items),
        "items": items,
        "detected": detect_identifier(text=query) if query else None,
        "note": note,
    }


def universe_filters(*, con: Connection) -> dict[str, object]:
    """The values for the asset-class and venue filters, and the universe totals."""
    return {
        "product_codes": queries.product_code_counts(con=con),
        "mics": queries.primary_venue_counts(con=con),
        "totals": queries.universe_totals(con=con),
    }


def exception_page(*, con: Connection, search: ExceptionSearch) -> dict[str, object]:
    """The exception queue with the per-reason counts."""
    items: list[Row] = queries.find_exceptions(con=con, search=search)
    return {
        "total": len(items),
        "reasons": queries.exception_reasons(con=con),
        "items": items,
    }


def issuer_page(*, con: Connection, search: IssuerSearch) -> dict[str, object]:
    """Every matching issuer with its instrument count."""
    items: list[Row] = queries.find_issuers(con=con, search=search)
    logger.debug(
        "issuers search q=%r sort=%s %s -> %d rows",
        search.q,
        search.sort,
        search.direction,
        len(items),
    )
    return {"total": len(items), "items": items}


def issuer_detail(*, con: Connection, issuer_id: int) -> dict[str, object]:
    """One issuer's record and its instruments.

    Raises:
        NotFoundError: If there is no such issuer.
    """
    issuer: Row | None = queries.issuer_of(con=con, issuer_id=issuer_id)
    if issuer is None:
        logger.info("issuer %d not found", issuer_id)
        raise NotFoundError(f"No issuer {issuer_id}.")
    return {
        "issuer": issuer,
        "instruments": queries.issuer_instruments(con=con, issuer_id=issuer_id),
    }


def attribute_gaps(
    *, issuer: Row, identifiers: list[Row], listings: list[Row]
) -> list[str]:
    """The attributes this instrument does not have, each with the reason."""
    gaps: list[str] = []
    if not any(row["scheme"] == "ISIN" for row in identifiers):
        gaps.append("ISIN: not held (no free authoritative CUSIP-keyed source)")
    gaps.append("SEDOL: not held (licensed)")
    if issuer["gics_code"] is None:
        gaps.append(
            f"GICS: not held (licensed); EDGAR SIC {issuer['sic'] or '—'} stands in"
        )
    if issuer["lei"] is None:
        gaps.append("LEI: not held (EDGAR gave none)")
    if all(row["currency"] is None for row in listings):
        gaps.append("Currency: not given by any source")
    if all(row["figi"] is None for row in listings):
        gaps.append(
            "Per-venue FIGI: not mapped (OpenFIGI gives exchange codes, not MICs)"
        )
    return gaps


def integrity_checks(
    *, product_code: str, terms: Row | None, underlying: Row | None, listings: list[Row]
) -> list[Row]:
    """The integrity rules that can be read off one instrument, each passed or failed."""
    checks: list[Row] = [
        {
            "rule": "R1",
            "label": "Has exactly one subtype row",
            "passed": terms is not None,
        },
        {"rule": "R2", "label": "Linked to an issuer", "passed": True},
        {"rule": "R11", "label": "Has at least one listing", "passed": len(listings) > 0},
        {
            "rule": "R12",
            "label": "At most one primary listing",
            "passed": sum(1 for row in listings if row["is_primary"]) <= 1,
        },
    ]
    if product_code in UNDERLYING_REQUIRED:
        checks.append(
            {
                "rule": "R3/R4",
                "label": "References an underlying equity",
                "passed": underlying is not None,
            }
        )
    return checks


def lineage_of(
    *, head: Row, issuer: Row, identifiers: list[Row], listings: list[Row]
) -> list[Row]:
    """Where each datapoint of the instrument came from, and as of when."""
    return [
        {
            "datapoint": "Instrument, product class, CUSIP",
            "source": head["source"],
            "as_of": head["as_of"],
        },
        *(
            {
                "datapoint": f"{row['scheme']} identifier",
                "source": row["source"],
                "as_of": row["as_of"],
            }
            for row in identifiers
        ),
        {
            "datapoint": "Issuer (name, SIC, country, CIK)",
            "source": issuer["source"],
            "as_of": issuer["as_of"],
        },
        *(
            {
                "datapoint": f"Listing {row['mic']} ({row['confidence']} confidence)",
                "source": row["source"],
                "as_of": row["as_of"],
            }
            for row in listings
        ),
    ]


def security_detail(*, con: Connection, instrument_id: int) -> dict[str, object]:
    """Everything known about one instrument.

    Args:
        con: A read-only connection.
        instrument_id: The internal instrument id.

    Returns:
        Taxonomy, issuer, identifiers, listings, terms, underlying, governance and lineage.

    Raises:
        NotFoundError: If there is no such instrument.
    """
    head: Row | None = queries.instrument_head(con=con, instrument_id=instrument_id)
    if head is None:
        logger.info("instrument %d not found", instrument_id)
        raise NotFoundError(f"No instrument {instrument_id}.")
    issuer: Row | None = queries.issuer_of(con=con, issuer_id=head["issuer_id"])
    if issuer is None:
        logger.error("instrument %d has no issuer row: the data breaks R2", instrument_id)
        raise NotFoundError(f"Instrument {instrument_id} has no issuer row.")
    identifiers: list[Row] = queries.identifiers_of(con=con, instrument_id=instrument_id)
    listings: list[Row] = queries.listings_of(con=con, instrument_id=instrument_id)
    terms: Row | None = queries.subtype_row(
        con=con, table=str(head["subtype_table"]), instrument_id=instrument_id
    )
    underlying: Row | None = None
    if terms and terms.get("underlying_instrument_id") is not None:
        underlying = queries.instrument_summary(
            con=con, instrument_id=terms["underlying_instrument_id"]
        )
    if terms:
        for key in DROPPED_TERM_KEYS:
            terms.pop(key, None)
    return {
        "instrument": {
            key: head[key]
            for key in (
                "instrument_id",
                "name",
                "product_code",
                "source",
                "as_of",
                "is_synthetic",
            )
        },
        "taxonomy": {
            key: head[key]
            for key in (
                "asset_class_code",
                "asset_class_name",
                "base_product_code",
                "base_product_name",
                "description",
                "taxonomy_source",
                "subtype_table",
                "desk_family",
                "cftc_asset_class",
                "mifid_category",
                "isda_path",
            )
        },
        "issuer": issuer,
        "identifiers": identifiers,
        "listings": listings,
        "terms": terms,
        "underlying": underlying,
        "governance": {
            "gaps": attribute_gaps(
                issuer=issuer, identifiers=identifiers, listings=listings
            ),
            "checks": integrity_checks(
                product_code=str(head["product_code"]),
                terms=terms,
                underlying=underlying,
                listings=listings,
            ),
        },
        "lineage": lineage_of(
            head=head, issuer=issuer, identifiers=identifiers, listings=listings
        ),
    }
