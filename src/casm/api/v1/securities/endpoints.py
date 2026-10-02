"""HTTP routes for the Securities Universe screen. Validation and wiring only; logic is in service.py.

Routes are async; the synchronous service call runs in a worker thread so the event loop is never blocked.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from casm.api.utils.database_utils import Connection, get_cursor
from casm.api.v1.models import ExceptionSearch, IssuerSearch, SecuritySearch
from casm.api.v1.securities import service

router: APIRouter = APIRouter(prefix="/api/v1", tags=["securities"])


@router.get("/securities")
async def list_securities(
    search: Annotated[SecuritySearch, Query()], con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """The whole instrument universe (unpaged): one row per instrument with its primary listing."""
    return await asyncio.to_thread(service.search_securities, con=con, search=search)


@router.get("/securities/filters")
async def security_filters(con: Connection = Depends(get_cursor)) -> dict[str, object]:
    """Values and counts for the asset-class and venue filters, and the universe totals."""
    return await asyncio.to_thread(service.universe_filters, con=con)


@router.get("/securities/{instrument_id}")
async def security_detail(
    instrument_id: int, con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """One instrument in full: taxonomy, issuer, identifiers, listings, terms, governance, lineage."""
    return await asyncio.to_thread(
        service.security_detail, con=con, instrument_id=instrument_id
    )


@router.get("/issuers")
async def list_issuers(
    search: Annotated[IssuerSearch, Query()], con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """Every issuer (unpaged) with its instrument count."""
    return await asyncio.to_thread(service.issuer_page, con=con, search=search)


@router.get("/issuers/{issuer_id}")
async def issuer_detail(
    issuer_id: int, con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """One issuer's record and its instruments; 404 if unknown."""
    return await asyncio.to_thread(service.issuer_detail, con=con, issuer_id=issuer_id)


@router.get("/exceptions")
async def list_exceptions(
    search: Annotated[ExceptionSearch, Query()], con: Connection = Depends(get_cursor)
) -> dict[str, object]:
    """Sampled filing rows that could not become an instrument (unpaged), each with its reason code."""
    return await asyncio.to_thread(service.exception_page, con=con, search=search)
