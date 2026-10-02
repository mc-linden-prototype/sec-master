"""Securities routes over HTTP: status codes, response shapes, validation errors."""

import pytest
from fastapi.testclient import TestClient

BASE: str = "/api/v1"


class TestListSecurities:
    def test_default_page(self, client: TestClient) -> None:
        response = client.get(f"{BASE}/securities")
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"total", "items", "detected", "note"}
        assert body["total"] == 398 and len(body["items"]) == 398  # never paged
        assert set(body["items"][0]) == {
            "instrument_id", "name", "product_code", "ticker", "mic", "confidence",
            "cusip", "figi", "country", "issuer", "underlying_name", "bbg_ticker", "composite_figi", "cik",
        }  # fmt: skip

    def test_search_by_cusip(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/securities", params={"q": "55306NAB0"}).json()
        assert body["total"] == 1 and body["detected"] == "CUSIP"
        assert body["items"][0]["name"] == "MKS INC 1.25 06/01/2030"

    def test_filters_and_sort_go_through_the_query_string(
        self, client: TestClient
    ) -> None:
        body = client.get(
            f"{BASE}/securities",
            params={
                "product_code": "EQ-SPT-WARRANT",
                "sort": "name",
                "direction": "desc",
            },
        ).json()
        assert body["total"] == 63 and len(body["items"]) == 63
        names = [item["name"] for item in body["items"]]
        assert names == sorted(names, reverse=True)

    def test_unsupported_scope_gets_a_note_not_an_error(self, client: TestClient) -> None:
        response = client.get(
            f"{BASE}/securities", params={"q": "US0378331005", "scope": "isin"}
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0 and "ISIN" in response.json()["note"]

    @pytest.mark.parametrize(
        "params",
        [
            {"limit": 5},  # securities are never paged
            {"offset": 0},
            {"scope": "isn"},
            {"sort": "price"},
            {"direction": "sideways"},
            {"mic": "XN"},
            {"q": "x" * 101},
            {"surprise": "1"},
        ],
    )
    def test_invalid_parameters_are_422_with_a_detail(
        self, client: TestClient, params: dict[str, object]
    ) -> None:
        response = client.get(f"{BASE}/securities", params=params)
        assert response.status_code == 422
        assert response.json()["detail"]

    def test_json_numbers_are_numbers(self, client: TestClient) -> None:
        bond_id = client.get(f"{BASE}/securities", params={"q": "55306NAB0"}).json()[
            "items"
        ][0]["instrument_id"]
        terms = client.get(f"{BASE}/securities/{bond_id}").json()["terms"]
        assert (
            isinstance(terms["coupon_rate"], float)
            and terms["maturity_date"] == "2030-06-01"
        )


class TestSecurityFilters:
    def test_returns_facets_and_totals(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/securities/filters").json()
        assert body["totals"] == {"instruments": 398, "exceptions": 22}
        assert len(body["product_codes"]) == 6 and len(body["mics"]) == 5

    def test_filters_is_not_mistaken_for_an_instrument_id(
        self, client: TestClient
    ) -> None:
        assert client.get(f"{BASE}/securities/filters").status_code == 200


class TestSecurityDetail:
    def test_detail_sections(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/securities/186").json()
        assert set(body) == {
            "instrument", "taxonomy", "issuer", "identifiers", "listings", "terms",
            "underlying", "governance", "lineage",
        }  # fmt: skip
        assert body["instrument"]["instrument_id"] == 186

    def test_unknown_id_is_404_with_a_message(self, client: TestClient) -> None:
        response = client.get(f"{BASE}/securities/999999")
        assert response.status_code == 404
        assert response.json() == {"detail": "No instrument 999999."}

    def test_non_numeric_id_is_422(self, client: TestClient) -> None:
        assert client.get(f"{BASE}/securities/abc").status_code == 422


class TestExceptions:
    def test_queue(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/exceptions").json()
        assert body["total"] == 22 and len(body["items"]) == 22
        assert {row["reason_code"] for row in body["reasons"]} == {
            "INVALID_IDENTIFIER", "ISSUER_UNRESOLVED", "VENUE_UNRESOLVED",
        }  # fmt: skip

    def test_filter_by_reason(self, client: TestClient) -> None:
        body = client.get(
            f"{BASE}/exceptions", params={"reason": "INVALID_IDENTIFIER"}
        ).json()
        assert body["total"] == 13 and len(body["items"]) == 13

    def test_the_queue_is_never_paged(self, client: TestClient) -> None:
        assert client.get(f"{BASE}/exceptions", params={"limit": 5}).status_code == 422


class TestIssuers:
    def test_all_issuers_unpaged(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/issuers").json()
        assert body["total"] == 213 and len(body["items"]) == 213
        assert set(body["items"][0]) == {
            "issuer_id", "legal_name", "issuer_type", "country", "country_name",
            "cik", "sic", "cusip6", "instruments",
        }  # fmt: skip

    def test_search_and_sort(self, client: TestClient) -> None:
        body = client.get(f"{BASE}/issuers", params={"q": "alphabet"}).json()
        assert [row["legal_name"] for row in body["items"]] == ["Alphabet Inc."]
        counts = [
            r["instruments"]
            for r in client.get(
                f"{BASE}/issuers", params={"sort": "instruments", "direction": "desc"}
            ).json()["items"]
        ]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.parametrize(
        "params", [{"sort": "revenue"}, {"direction": "up"}, {"limit": 5}]
    )
    def test_invalid_parameters_are_422(
        self, client: TestClient, params: dict[str, object]
    ) -> None:
        assert client.get(f"{BASE}/issuers", params=params).status_code == 422

    def test_detail(self, client: TestClient) -> None:
        issuer_id = client.get(f"{BASE}/issuers", params={"q": "alphabet"}).json()[
            "items"
        ][0]["issuer_id"]
        body = client.get(f"{BASE}/issuers/{issuer_id}").json()
        assert (
            body["issuer"]["legal_name"] == "Alphabet Inc."
            and len(body["instruments"]) == 2
        )

    def test_unknown_issuer_is_404_and_bad_id_is_422(self, client: TestClient) -> None:
        assert client.get(f"{BASE}/issuers/999999").status_code == 404
        assert client.get(f"{BASE}/issuers/abc").status_code == 422
