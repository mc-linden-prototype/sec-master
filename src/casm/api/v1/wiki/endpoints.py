"""HTTP routes for the Wiki tab. Async; the file reads run in a worker thread."""

import asyncio

from fastapi import APIRouter, Request

from casm.api.v1.wiki import service

router: APIRouter = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])


@router.get("")
async def list_pages(request: Request) -> list[dict[str, str]]:
    """The wiki pages in reading order."""
    return await asyncio.to_thread(service.list_pages, **request.app.state.wiki)


@router.get("/{page_id}")
async def read_page(page_id: str, request: Request) -> dict[str, str]:
    """One wiki page as markdown, front matter removed."""
    return await asyncio.to_thread(
        service.read_page, **request.app.state.wiki, page_id=page_id
    )
