"""Business logic for the Reference Data screen where there is more than a query: the left rail, venues."""

import logging

from casm.api.errors import NotFoundError
from casm.api.utils.database_utils import Connection, Row
from casm.api.v1.models import VenueSearch
from casm.api.v1.reference import queries


def reference_sets(*, con: Connection, set_meta: list[dict[str, object]]) -> list[Row]:
    """The left-rail sets: each source file's metadata with its row count and a badge."""
    counts: dict[str, int] = queries.set_counts(con=con)
    badges: dict[str, str] = {
        "venues": f"{counts['venues']} / {counts['registry']:,}",
        "gics": "4 lvls",
        "taxonomy": str(counts["taxonomy"]),
        "countries": str(counts["countries"]),
        "isda": str(counts["isda"]),
    }
    return [
        {**meta, "count": counts[str(meta["id"])], "badge": badges[str(meta["id"])]}
        for meta in set_meta
    ]


logger: logging.Logger = logging.getLogger(__name__)
GICS_LEVELS: tuple[tuple[str, str], ...] = (
    ("Sector", "sector"),
    ("Industry Group", "industry_group"),
    ("Industry", "industry"),
    ("Sub-Industry", "sub_industry"),
)


def gics_hierarchy(*, flat: list[Row]) -> list[Row]:
    """Every GICS node at all four levels, in code order so each parent precedes its children.

    The table stores one row per sub-industry with its ancestors alongside; this turns that into one row per
    node: level, code, name, parent code and name, number of children, and (for a sub-industry) its definition.
    """
    nodes: dict[str, Row] = {}
    for row in flat:
        parent_code: str | None = None
        parent_name: str | None = None
        for number, (label, prefix) in enumerate(GICS_LEVELS, start=1):
            code: str = str(row[f"{prefix}_code"])
            name: str = str(row[f"{prefix}_name"])
            if code not in nodes:
                nodes[code] = {
                    "level": label,
                    "level_no": number,
                    "code": code,
                    "name": name,
                    "parent_code": parent_code,
                    "parent_name": parent_name,
                    "children": 0,
                    "description": (
                        row["sub_industry_description"] if number == 4 else None
                    ),
                    "issuers": row["issuers"] if number == 4 else 0,
                }
                if parent_code is not None:
                    nodes[parent_code]["children"] = int(nodes[parent_code]["children"]) + 1  # type: ignore[arg-type]
            parent_code, parent_name = code, name
    return sorted(nodes.values(), key=lambda node: str(node["code"]))


def gics_page(*, con: Connection) -> dict[str, object]:
    """The GICS level counts and every node of the hierarchy."""
    return {
        "levels": queries.gics_levels(con=con),
        "items": gics_hierarchy(flat=queries.gics_rows(con=con)),
    }


def venue_page(*, con: Connection, search: VenueSearch) -> dict[str, object]:
    """Every matching venue (unpaged) with the facets for the filters."""
    items: list[Row] = queries.find_venues(con=con, search=search)
    logger.debug(
        "venues search q=%r loaded=%s country=%s type=%s -> %d rows",
        search.q,
        search.loaded,
        search.country,
        search.venue_type,
        len(items),
    )
    return {
        "total": len(items),
        "items": items,
        "facets": queries.venue_facets(con=con, loaded=search.loaded),
    }


def venue_detail(
    *, con: Connection, mic: str, source: dict[str, object] | None
) -> dict[str, object]:
    """One venue: registry record, how CASM uses it and the instruments listed on it.

    Args:
        con: A read-only connection.
        mic: The market identifier code, any case.
        source: The pinned-file metadata of the venues set.

    Raises:
        NotFoundError: If the MIC is not in the ISO 10383 registry.
    """
    code: str = mic.upper()
    registry: Row | None = queries.registry_record(con=con, mic=code)
    if registry is None:
        logger.info("MIC %s not found in the registry", mic)
        raise NotFoundError(f"No MIC {mic} in the ISO 10383 registry.")
    return {
        "registry": registry,
        "venue": queries.loaded_venue(con=con, mic=code),
        "usage": queries.venue_usage(con=con, mic=code),
        "assets": queries.venue_assets(con=con, mic=code),
        "source": source,
    }
