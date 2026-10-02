"""HTTP routes for the Reference Data screen. Validation and wiring only.

Routes are async; the synchronous query or service call runs in a worker thread.
"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from casm.api.errors import NotFoundError
from casm.api.utils.database_utils import Connection, Row, get_cursor
from casm.api.v1.models import VenueSearch
from casm.api.v1.reference import queries, service

logger: logging.Logger = logging.getLogger(__name__)
router: APIRouter = APIRouter(prefix="/api/v1/reference", tags=["reference"])


@router.get("/sets")
async def reference_sets(
    request: Request, con: Connection = Depends(get_cursor)
) -> list[Row]:
    """The reference sets in the left rail, each with its row count and pinned source file."""
    return await asyncio.to_thread(
        service.reference_sets, con=con, set_meta=request.app.state.set_meta
    )


@router.get("/venues")
async def list_venues(
    search: Annotated[VenueSearch, Query()], con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """Venues loaded into CASM, or the whole ISO 10383 registry with `loaded=false`."""
    return await asyncio.to_thread(service.venue_page, con=con, search=search)


@router.get("/venues/{mic}")
async def venue_detail(
    mic: str, request: Request, con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """One venue's registry record, CASM usage and listed instruments."""
    source: dict[str, object] | None = next(
        (meta for meta in request.app.state.set_meta if meta["id"] == "venues"), None
    )
    return await asyncio.to_thread(service.venue_detail, con=con, mic=mic, source=source)


@router.get("/gics")
async def gics(con: Connection = Depends(get_cursor)) -> dict[str, object]:
    """The GICS hierarchy (2018 structure) at all four levels, with level counts."""
    return await asyncio.to_thread(service.gics_page, con=con)


@router.get("/taxonomy")
async def taxonomy(con: Connection = Depends(get_cursor)) -> dict[str, object]:
    """The Phase 1 product codes with asset class, base product and instrument counts."""
    return {"items": await asyncio.to_thread(queries.taxonomy_rows, con=con)}


@router.get("/taxonomy/{code}/instruments")
async def taxonomy_instruments(
    code: str, con: Connection = Depends(get_cursor)
) -> list[Row]:
    """A sample of the instruments carrying one product code."""
    if not await asyncio.to_thread(queries.product_code_exists, con=con, code=code):
        logger.info("product code %s not found", code)
        raise NotFoundError(f"No product code {code}.")
    return await asyncio.to_thread(queries.instruments_with_product, con=con, code=code)


@router.get("/countries")
async def countries(con: Connection = Depends(get_cursor)) -> dict[str, object]:
    """The ISO 3166-1 countries with the number of issuers and loaded venues in each."""
    return {"items": await asyncio.to_thread(queries.country_rows, con=con)}


@router.get("/countries/{alpha2}/issuers")
async def country_issuers(
    alpha2: str, con: Connection = Depends(get_cursor)
) -> list[Row]:
    """The issuers incorporated in one country."""
    code: str = alpha2.upper()
    if not await asyncio.to_thread(queries.country_exists, con=con, alpha2=code):
        logger.info("country %s not found", alpha2)
        raise NotFoundError(f"No country {alpha2} in ISO 3166-1.")
    return await asyncio.to_thread(queries.issuers_in_country, con=con, alpha2=code)


@router.get("/isda-equity")
async def isda_equity(con: Connection = Depends(get_cursor)) -> dict[str, object]:
    """The ISDA taxonomy v2.0 equity rows."""
    return {"items": await asyncio.to_thread(queries.isda_rows, con=con)}
