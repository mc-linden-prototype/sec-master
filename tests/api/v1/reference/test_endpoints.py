"""Reference routes over HTTP: status codes, shapes, validation and 404s."""

import pytest
from fastapi.testclient import TestClient

BASE: str = "/api/v1/reference"


class TestSets:
    def test_left_rail(self, client: TestClient) -> None:
        sets = client.get(f"{BASE}/sets").json()
        assert [row["id"] for row in sets] == [
            "venues",
            "gics",
            "taxonomy",
            "countries",
            "isda",
        ]
        venues = sets[0]
        assert venues["file"] == "ISO10383_MIC.xlsx" and venues["badge"] == "13 / 2,883"
        assert len(venues["sha256"]) == 64  # the pinned workbook is hashed

    def test_taxonomy_set_is_hashed_from_its_migration(self, client: TestClient) -> None:
        taxonomy = next(
            row for row in client.get(f"{BASE}/sets").json() if row["id"] == "taxonomy"
        )
        assert (
            taxonomy["file"] == "02_products_taxonomy.sql"
            and len(taxonomy["sha256"]) == 64
        )


class TestVenues:
    def test_default_page(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/venues").json()
        assert body["total"] == 2883 and set(body) == {
            "total",
            "items",
            "facets",
        }  # whole registry by default
        assert set(body["items"][0]) == {
            "mic", "operating_mic", "name", "country", "venue_type", "status", "listings", "loaded",
        }  # fmt: skip

    def test_registry_search(self, client: TestClient) -> None:
        body = client.get(
            f"{BASE}/venues", params={"q": "nasdaq", "loaded": "false"}
        ).json()
        assert body["total"] > 3 and len(body["items"]) == body["total"]

    def test_loaded_true_narrows_to_the_loaded_venues(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/venues", params={"loaded": "true"}).json()
        assert body["total"] == 13 and all(item["loaded"] for item in body["items"])

    def test_the_whole_registry_is_returned_unpaged(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/venues", params={"loaded": "false"}).json()
        assert body["total"] == 2883 and len(body["items"]) == 2883

    @pytest.mark.parametrize(
        "params",
        [
            {"venue_type": "DARKPOOL"},
            {"country": "USA"},
            {"sort": "listings_count"},
            {"limit": 5},  # venues are never paged
            {"offset": 5},
            {"loaded": "maybe"},
            {"direction": "up"},
        ],
    )
    def test_invalid_parameters_are_422(
        self, client: TestClient, params: dict[str, object]
    ) -> None:
        assert client.get(f"{BASE}/venues", params=params).status_code == 422

    def test_detail(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/venues/XNAS").json()
        assert body["registry"]["market_name"] == "NASDAQ - ALL MARKETS"
        assert body["source"]["id"] == "venues"

    def test_detail_unknown_mic_is_404(self, client: TestClient) -> None:
        response = client.get(f"{BASE}/venues/ZZZZ")
        assert response.status_code == 404 and "ZZZZ" in response.json()["detail"]


class TestStaticSets:
    def test_gics(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/gics").json()
        assert (
            body["levels"]["sub_industries"] == 158 and len(body["items"]) == 262
        )  # all four levels

    def test_taxonomy(self, client: TestClient) -> None:
        assert len(client.get(f"{BASE}/taxonomy").json()["items"]) == 17

    def test_taxonomy_instruments(self, client: TestClient) -> None:
        assert len(client.get(f"{BASE}/taxonomy/EQ-SPT-UNIT/instruments").json()) == 7

    def test_taxonomy_instruments_for_a_code_with_none(self, client: TestClient) -> None:
        response = client.get(f"{BASE}/taxonomy/EQ-OPT-VANILLA/instruments")
        assert response.status_code == 200 and response.json() == []

    def test_taxonomy_instruments_unknown_code_is_404(self, client: TestClient) -> None:
        assert client.get(f"{BASE}/taxonomy/NOPE/instruments").status_code == 404

    def test_countries(self, client: TestClient) -> None:
        assert len(client.get(f"{BASE}/countries").json()["items"]) == 249

    def test_country_issuers_any_case(self, client: TestClient) -> None:
        assert (
            client.get(f"{BASE}/countries/ky/issuers").json()
            == client.get(f"{BASE}/countries/KY/issuers").json()
        )

    def test_country_issuers_unknown_is_404(self, client: TestClient) -> None:
        assert client.get(f"{BASE}/countries/XX/issuers").status_code == 404

    def test_isda(self, client: TestClient) -> None:
        assert len(client.get(f"{BASE}/isda-equity").json()["items"]) == 34
