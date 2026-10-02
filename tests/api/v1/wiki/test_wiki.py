"""Wiki service and routes: reading order, front matter removal and unknown pages."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from casm.api.errors import NotFoundError
from casm.api.v1.wiki import service


@pytest.fixture
def wiki(tmp_path: Path) -> tuple[Path, Path]:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "1_1-second.md").write_text(
        "---\nname: s\ndescription: d\n---\n\n# Second page\n\ntext", encoding="utf-8"
    )
    (docs / "1_0-first.md").write_text("# First page\n\nbody", encoding="utf-8")
    (docs / "notes.txt").write_text("not markdown", encoding="utf-8")
    index = tmp_path / "README.md"
    index.write_text("---\nname: i\ndescription: d\n---\n\n# README\n", encoding="utf-8")
    return docs, index


class TestService:
    def test_index_comes_first_then_pages_in_name_order(
        self, wiki: tuple[Path, Path]
    ) -> None:
        pages = service.list_pages(wiki_dir=wiki[0], index_file=wiki[1])
        assert [p["id"] for p in pages] == ["index", "1_0-first", "1_1-second"]
        assert [p["title"] for p in pages] == [
            "README",
            "First page",
            "Second page",
        ]

    def test_only_markdown_files_are_pages(self, wiki: tuple[Path, Path]) -> None:
        ids = [p["id"] for p in service.list_pages(wiki_dir=wiki[0], index_file=wiki[1])]
        assert "notes" not in ids

    def test_front_matter_is_removed(self, wiki: tuple[Path, Path]) -> None:
        page = service.read_page(
            wiki_dir=wiki[0], index_file=wiki[1], page_id="1_1-second"
        )
        assert (
            not page["markdown"].lstrip().startswith("---")
            and "description: d" not in page["markdown"]
        )
        assert page["markdown"].lstrip().startswith("# Second page")

    def test_page_without_front_matter_is_unchanged(
        self, wiki: tuple[Path, Path]
    ) -> None:
        page = service.read_page(wiki_dir=wiki[0], index_file=wiki[1], page_id="1_0-first")
        assert page["markdown"] == "# First page\n\nbody"

    def test_title_falls_back_to_the_file_name(self) -> None:
        assert service.split_page(text="no heading here", fallback_title="x") == (
            "x",
            "no heading here",
        )

    @pytest.mark.parametrize(
        "page_id", ["missing", "../README", "..%2fsecret", "notes", ""]
    )
    def test_unknown_or_unlisted_id_is_not_found(
        self, wiki: tuple[Path, Path], page_id: str
    ) -> None:
        with pytest.raises(NotFoundError):
            service.read_page(wiki_dir=wiki[0], index_file=wiki[1], page_id=page_id)


class TestRoutes:
    def test_the_real_wiki_lists_in_reading_order(self, client: TestClient) -> None:
        pages = client.get("/api/v1/wiki").json()
        ids = [p["id"] for p in pages]
        assert (
            ids[0] == "index"
            and ids[1:] == sorted(ids[1:])
            and "3_1-database-schema" in ids
        )

    def test_read_a_real_page(self, client: TestClient) -> None:
        page = client.get("/api/v1/wiki/3_1-database-schema").json()
        assert (
            page["title"].startswith("Database")
            and "name: database-design" not in page["markdown"]
        )

    def test_unknown_page_is_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/wiki/nope").status_code == 404

    def test_path_traversal_is_not_possible(self, client: TestClient) -> None:
        assert client.get("/api/v1/wiki/..%2f..%2fCLAUDE").status_code == 404
