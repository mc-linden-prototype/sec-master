"""Reads the wiki: the index file first, then the numbered pages in name order."""

import logging
import re
from pathlib import Path

from casm.api.errors import NotFoundError

logger: logging.Logger = logging.getLogger(__name__)
INDEX_ID: str = "index"
FRONT_MATTER: re.Pattern[str] = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.S)
HEADING: re.Pattern[str] = re.compile(r"^#\s+(.+)$", re.M)


def page_files(*, wiki_dir: Path, index_file: Path) -> dict[str, Path]:
    """Page id to file, in reading order: `index` (README.md), then 1_0-..., 1_1-... by name."""
    pages: dict[str, Path] = {INDEX_ID: index_file}
    for path in sorted(wiki_dir.glob("*.md")):
        pages[path.stem] = path
    return pages


def split_page(*, text: str, fallback_title: str) -> tuple[str, str]:
    """Return (title, markdown) with the YAML front matter removed; the title is the first heading."""
    body: str = FRONT_MATTER.sub("", text, count=1)
    heading: re.Match[str] | None = HEADING.search(body)
    return (heading.group(1).strip() if heading else fallback_title), body


def list_pages(*, wiki_dir: Path, index_file: Path) -> list[dict[str, str]]:
    """Every wiki page's id and title, in reading order."""
    pages: list[dict[str, str]] = []
    for page_id, path in page_files(wiki_dir=wiki_dir, index_file=index_file).items():
        title, _ = split_page(
            text=path.read_text(encoding="utf-8"), fallback_title=path.stem
        )
        pages.append({"id": page_id, "title": title, "file": path.name})
    return pages


def read_page(*, wiki_dir: Path, index_file: Path, page_id: str) -> dict[str, str]:
    """One page's markdown.

    Raises:
        NotFoundError: If `page_id` is not in the listing. Only listed files are ever read.
    """
    path: Path | None = page_files(wiki_dir=wiki_dir, index_file=index_file).get(page_id)
    if path is None:
        logger.info("wiki page %r not found", page_id)
        raise NotFoundError(f"No wiki page {page_id}.")
    title, markdown = split_page(
        text=path.read_text(encoding="utf-8"), fallback_title=path.stem
    )
    return {"id": page_id, "title": title, "file": path.name, "markdown": markdown}
