"""Reference service and queries against the real seeded database."""

import duckdb
import pytest

from casm.api.errors import NotFoundError
from casm.api.v1.models import VenueSearch
from casm.api.v1.reference import queries, service

SET_META: list[dict[str, object]] = [
    {"id": set_id, "label": set_id, "icon": "x", "file": f"{set_id}.file", "sha256": None}
    for set_id in ("venues", "gics", "taxonomy", "countries", "isda")
]


def venues(con: duckdb.DuckDBPyConnection, **kwargs: object) -> dict[str, object]:
    kwargs.setdefault(
        "loaded", True
    )  # most tests exercise the 13 loaded venues; the default is tested below
    return service.venue_page(con=con, search=VenueSearch(**kwargs))


def mics(page: dict[str, object]) -> list[str]:
    return [str(item["mic"]) for item in page["items"]]  # type: ignore[union-attr]


class TestReferenceSets:
    def test_counts_and_badges(self, con: duckdb.DuckDBPyConnection) -> None:
        sets = {
            row["id"]: row for row in service.reference_sets(con=con, set_meta=SET_META)
        }
        assert {key: row["count"] for key, row in sets.items()} == {
            "venues": 13, "gics": 158, "taxonomy": 17, "countries": 249, "isda": 34,
        }  # fmt: skip
        assert sets["venues"]["badge"] == "13 / 2,883"
        assert sets["gics"]["badge"] == "4 lvls"

    def test_metadata_is_carried_through(self, con: duckdb.DuckDBPyConnection) -> None:
        first = service.reference_sets(con=con, set_meta=SET_META)[0]
        assert first["file"] == "venues.file" and first["sha256"] is None


class TestVenuePage:
    def test_the_default_is_the_whole_registry(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        page = service.venue_page(con=con, search=VenueSearch())
        assert page["total"] == 2883 and len(page["items"]) == 2883  # type: ignore[arg-type]
        assert sum(1 for item in page["items"] if item["loaded"]) == 13  # type: ignore[union-attr]

    def test_loaded_true_narrows_to_the_venues_loaded_into_casm(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        page = venues(con)
        assert page["total"] == 13
        assert set(mics(page)) >= {"XNAS", "XNYS", "XASE", "ARCX", "XOFF", "XXXX"}
        assert all(item["loaded"] for item in page["items"])  # type: ignore[union-attr]

    def test_full_registry(self, con: duckdb.DuckDBPyConnection) -> None:
        page = venues(con, loaded=False)
        assert page["total"] == 2883 and len(page["items"]) == 2883  # type: ignore[arg-type]

    def test_search_matches_mic_name_and_operating_mic(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert mics(venues(con, q="xnas")) == ["XNAS"]
        assert "XNYS" in mics(venues(con, q="new york stock"))
        assert {"XNYS", "ARCX", "XASE"} <= set(mics(venues(con, q="XNYS")))

    def test_search_widens_to_unloaded_venues_when_asked(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        page = venues(con, q="nasdaq", loaded=False)
        assert page["total"] > 10 and any(not item["loaded"] for item in page["items"])  # type: ignore[union-attr]

    def test_venue_type_filter(self, con: duckdb.DuckDBPyConnection) -> None:
        assert mics(venues(con, venue_type="OTC")) == ["XOFF"]
        assert mics(venues(con, venue_type="NONE")) == ["XXXX"]

    def test_venue_type_implies_loaded(self, con: duckdb.DuckDBPyConnection) -> None:
        assert venues(con, venue_type="EXCHANGE", loaded=False)["total"] == 11

    def test_country_filter_and_the_placeholders_country(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert venues(con, country="us")["total"] == 11
        assert set(mics(venues(con, country="ZZ"))) == {"XOFF", "XXXX"}

    def test_status_filter(self, con: duckdb.DuckDBPyConnection) -> None:
        assert venues(con, status="ACTIVE")["total"] == 13
        assert venues(con, status="EXPIRED")["total"] == 0

    def test_listing_counts(self, con: duckdb.DuckDBPyConnection) -> None:
        listings = {item["mic"]: item["listings"] for item in venues(con)["items"]}  # type: ignore[union-attr]
        assert (
            listings["XNAS"] == 249 and listings["XOFF"] == 76 and listings["XXXX"] == 18
        )
        assert listings["ARCX"] == 0

    def test_sorting(self, con: duckdb.DuckDBPyConnection) -> None:
        by_listings = [item["listings"] for item in venues(con, sort="listings", direction="desc")["items"]]  # type: ignore[union-attr]
        assert by_listings == sorted(by_listings, reverse=True)
        assert mics(venues(con, direction="desc")) == sorted(
            mics(venues(con)), reverse=True
        )

    def test_wildcard_text_matches_literally(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert venues(con, q="%", loaded=False)["total"] == 0

    def test_facets_follow_the_scope(self, con: duckdb.DuckDBPyConnection) -> None:
        loaded = venues(con)["facets"]
        assert loaded["countries"] == ["US", "ZZ"] and loaded["statuses"] == ["ACTIVE"]  # type: ignore[index]
        assert loaded["types"] == ["EXCHANGE", "NONE", "OTC"]  # type: ignore[index]
        assert len(venues(con, loaded=False)["facets"]["countries"]) > 50  # type: ignore[index]


class TestVenueDetail:
    def test_loaded_venue(self, con: duckdb.DuckDBPyConnection) -> None:
        detail = service.venue_detail(con=con, mic="XNAS", source={"file": "f"})
        assert detail["registry"]["operating_mic"] == "XNAS" and detail["registry"]["country"] == "US"  # type: ignore[index]
        assert detail["venue"]["venue_type"] == "EXCHANGE" and detail["venue"]["is_otc"] is False  # type: ignore[index]
        assert detail["usage"]["listings"] == 249 and detail["usage"]["total_instruments"] == 398  # type: ignore[index]
        assert sum(row["count"] for row in detail["usage"]["by_product"]) == 249  # type: ignore[index]
        assert detail["source"] == {"file": "f"}

    def test_mic_is_case_insensitive(self, con: duckdb.DuckDBPyConnection) -> None:
        assert service.venue_detail(con=con, mic="xnys", source=None)["registry"]["mic"] == "XNYS"  # type: ignore[index]

    def test_segment_names_its_operating_venue(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        registry = service.venue_detail(con=con, mic="ARCX", source=None)["registry"]
        assert registry["operating_mic"] == "XNYS" and "NEW YORK STOCK EXCHANGE" in registry["operating_name"]  # type: ignore[index]

    def test_otc_placeholder_is_otc(self, con: duckdb.DuckDBPyConnection) -> None:
        detail = service.venue_detail(con=con, mic="XOFF", source=None)
        assert detail["venue"]["is_otc"] is True and detail["usage"]["listings"] == 76  # type: ignore[index]

    def test_assets_are_the_instruments_listed_there(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assets = service.venue_detail(con=con, mic="XXXX", source=None)["assets"]
        assert len(assets) == 18 and all(asset["product_code"] == "FI-BND-CONV" for asset in assets)  # type: ignore[arg-type,union-attr]

    def test_assets_are_every_listing_not_capped(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert (
            len(service.venue_detail(con=con, mic="XNAS", source=None)["assets"]) == 249
        )  # every listing, not capped  # type: ignore[arg-type]

    def test_registry_venue_that_is_not_loaded_has_no_casm_data(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        detail = service.venue_detail(con=con, mic="XLON", source=None)
        assert detail["venue"] is None and detail["usage"]["listings"] == 0 and detail["assets"] == []  # type: ignore[index]

    @pytest.mark.parametrize("mic", ["ZZZZ", "", "xnas1"])
    def test_unknown_mic_raises_not_found(
        self, con: duckdb.DuckDBPyConnection, mic: str
    ) -> None:
        with pytest.raises(NotFoundError, match="registry"):
            service.venue_detail(con=con, mic=mic, source=None)


class TestGicsHierarchy:
    @pytest.fixture
    def nodes(self, con: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
        return service.gics_page(con=con)["items"]  # type: ignore[return-value]

    def test_all_four_levels_are_present(
        self, con: duckdb.DuckDBPyConnection, nodes: list[dict[str, object]]
    ) -> None:
        page = service.gics_page(con=con)
        assert page["levels"] == {
            "sectors": 11,
            "groups": 24,
            "industries": 69,
            "sub_industries": 158,
        }
        counts = {
            level: sum(1 for n in nodes if n["level"] == level)
            for level in ("Sector", "Industry Group", "Industry", "Sub-Industry")
        }
        assert counts == {
            "Sector": 11,
            "Industry Group": 24,
            "Industry": 69,
            "Sub-Industry": 158,
        }
        assert len(nodes) == 262

    def test_code_order_puts_each_parent_before_its_children(
        self, nodes: list[dict[str, object]]
    ) -> None:
        position = {n["code"]: i for i, n in enumerate(nodes)}
        assert [n["code"] for n in nodes] == sorted(position)
        for node in nodes:
            if node["parent_code"]:
                assert position[node["parent_code"]] < position[node["code"]]

    def test_codes_nest_by_prefix_and_lengths_follow_the_level(
        self, nodes: list[dict[str, object]]
    ) -> None:
        lengths = {"Sector": 2, "Industry Group": 4, "Industry": 6, "Sub-Industry": 8}
        for node in nodes:
            assert len(str(node["code"])) == lengths[str(node["level"])]
            if node["parent_code"]:
                assert str(node["code"]).startswith(str(node["parent_code"]))

    def test_a_known_chain(self, nodes: list[dict[str, object]]) -> None:
        by_code = {n["code"]: n for n in nodes}
        assert by_code["10"]["name"] == "Energy" and by_code["10"]["parent_code"] is None
        assert by_code["1010"]["parent_code"] == "10"
        assert by_code["101010"]["name"] == "Energy Equipment & Services"
        sub = by_code["10101010"]
        assert (sub["name"], sub["parent_code"], sub["parent_name"]) == (
            "Oil & Gas Drilling",
            "101010",
            "Energy Equipment & Services",
        )
        assert "Drilling contractors" in str(sub["description"])

    def test_child_counts_add_up_across_levels(
        self, nodes: list[dict[str, object]]
    ) -> None:
        for level, child_level in (
            ("Sector", "Industry Group"),
            ("Industry Group", "Industry"),
            ("Industry", "Sub-Industry"),
        ):
            parents = sum(int(n["children"]) for n in nodes if n["level"] == level)  # type: ignore[arg-type]
            assert parents == sum(1 for n in nodes if n["level"] == child_level)
        assert all(n["children"] == 0 for n in nodes if n["level"] == "Sub-Industry")

    def test_only_sub_industries_carry_a_definition(
        self, nodes: list[dict[str, object]]
    ) -> None:
        assert all(
            (n["description"] is None) == (n["level"] != "Sub-Industry") for n in nodes
        )


class TestStaticReferenceSets:
    def test_gics(self, con: duckdb.DuckDBPyConnection) -> None:
        assert queries.gics_levels(con=con) == {
            "sectors": 11,
            "groups": 24,
            "industries": 69,
            "sub_industries": 158,
        }
        rows = queries.gics_rows(con=con)
        assert len(rows) == 158 and rows[0]["sub_industry_code"] == "10101010"
        assert all(row["issuers"] == 0 for row in rows)  # no issuer carries a GICS code

    def test_taxonomy(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = {row["code"]: row for row in queries.taxonomy_rows(con=con)}
        assert len(rows) == 17
        assert (
            rows["EQ-SPT-COMMON"]["instruments"] == 201
            and rows["EQ-SPT-COMMON"]["asset_class_name"] == "Equity"
        )
        assert (
            rows["EQ-OPT-VANILLA"]["instruments"] == 0
            and rows["EQ-OPT-VANILLA"]["mifid_category"] == "C5"
        )
        assert rows["FI-BND-CONV"]["base_product_name"] == "Bond"

    def test_taxonomy_instruments(self, con: duckdb.DuckDBPyConnection) -> None:
        sample = queries.instruments_with_product(con=con, code="EQ-SPT-UNIT")
        assert len(sample) == 7 and all(row["cusip"] for row in sample)
        assert queries.instruments_with_product(con=con, code="EQ-OPT-VANILLA") == []

    def test_product_code_exists(self, con: duckdb.DuckDBPyConnection) -> None:
        assert queries.product_code_exists(con=con, code="FI-BND-CONV")
        assert not queries.product_code_exists(con=con, code="NOPE")

    def test_countries(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = {row["alpha2"]: row for row in queries.country_rows(con=con)}
        assert len(rows) == 249 and rows["US"]["venues"] == 11
        assert rows["KY"]["issuers"] > 100 and rows["AF"]["issuers"] == 0
        assert sum(row["issuers"] for row in rows.values()) <= 213

    def test_country_issuers(self, con: duckdb.DuckDBPyConnection) -> None:
        issuers = queries.issuers_in_country(con=con, alpha2="KY")
        assert issuers and all(row["instruments"] >= 1 for row in issuers)
        assert queries.issuers_in_country(con=con, alpha2="AF") == []

    def test_country_exists(self, con: duckdb.DuckDBPyConnection) -> None:
        assert queries.country_exists(
            con=con, alpha2="US"
        ) and not queries.country_exists(con=con, alpha2="XX")

    def test_isda(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = queries.isda_rows(con=con)
        assert (
            len(rows) == 34
            and rows[0]["isda_row_no"] == 1
            and rows[-1]["sub_product"] is None
        )
