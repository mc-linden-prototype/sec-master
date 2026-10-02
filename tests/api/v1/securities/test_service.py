"""Securities service and queries against the real seeded database (398 instruments, 22 queued rows)."""

import duckdb
import pytest

from casm.api.errors import NotFoundError
from casm.api.v1.models import ExceptionSearch, IssuerSearch, SecuritySearch
from casm.api.v1.securities import service

PRODUCT_COUNTS: dict[str, int] = {
    "EQ-SPT-COMMON": 201,
    "EQ-SPT-DEP-RCPT": 6,
    "EQ-SPT-RIGHTS": 27,
    "EQ-SPT-UNIT": 7,
    "EQ-SPT-WARRANT": 63,
    "FI-BND-CONV": 94,
}
MKS_CUSIP: str = "55306NAB0"


def search(con: duckdb.DuckDBPyConnection, **kwargs: object) -> dict[str, object]:
    return service.search_securities(con=con, search=SecuritySearch(**kwargs))


def names(result: dict[str, object]) -> list[str]:
    return [str(item["name"]) for item in result["items"]]  # type: ignore[union-attr]


def instrument_id(con: duckdb.DuckDBPyConnection, cusip: str) -> int:
    items = search(con, q=cusip, scope="cusip")["items"]
    assert len(items) == 1, f"expected exactly one instrument for {cusip}"
    return int(items[0]["instrument_id"])  # type: ignore[index]


class TestDetectIdentifier:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("BBG01MVF4CQ3", "FIGI"),
            ("bbg01mvf4cq3", "FIGI"),
            ("US0378331005", "ISIN"),
            ("55306NAB0", "CUSIP"),
            ("  02079K107 ", "CUSIP"),
            ("G6757R105", "CUSIP"),
            ("2046251", "SEDOL"),
            ("AAPL", None),
            ("MKS INC", None),
            ("", None),
        ],
    )
    def test_detects_type(self, text: str, expected: str | None) -> None:
        assert service.detect_identifier(text=text) == expected


class TestSearchSecurities:
    def test_no_filter_returns_the_whole_universe(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        result = search(con)
        assert result["total"] == 398
        assert len(result["items"]) == 398  # never paged
        assert result["detected"] is None and result["note"] is None

    def test_row_shape_and_values(self, con: duckdb.DuckDBPyConnection) -> None:
        row = search(con, q=MKS_CUSIP)["items"][0]  # type: ignore[index]
        assert row["name"] == "MKS INC 1.25 06/01/2030"
        assert (row["product_code"], row["cusip"], row["mic"]) == (
            "FI-BND-CONV",
            MKS_CUSIP,
            "XOFF",
        )
        assert row["ticker"] is None  # a bond has no exchange symbol
        assert row["figi"].startswith("BBG") and row["country"] == "US"

    def test_cusip_search_detects_the_identifier(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        result = search(con, q=MKS_CUSIP)
        assert (result["total"], result["detected"]) == (1, "CUSIP")

    def test_cusip_scope_is_a_prefix_match(self, con: duckdb.DuckDBPyConnection) -> None:
        assert search(con, q="55306N", scope="cusip")["total"] == 1
        assert search(con, q="306NAB", scope="cusip")["total"] == 0

    def test_ticker_scope(self, con: duckdb.DuckDBPyConnection) -> None:
        result = search(con, q="GOOG", scope="ticker", sort="ticker")
        assert [item["ticker"] for item in result["items"]] == ["GOOG", "GOOGL"]  # type: ignore[union-attr]

    def test_name_scope_is_a_contains_match_and_ignores_case(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert "ALPHABET INC CL C" in names(search(con, q="alphabet", scope="name"))

    def test_figi_scope_finds_the_instrument(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        figi = search(con, q=MKS_CUSIP)["items"][0]["figi"]  # type: ignore[index]
        found = search(con, q=figi, scope="figi")
        assert (found["total"], found["detected"]) == (1, "FIGI")

    @pytest.mark.parametrize("scope", ["isin", "sedol"])
    def test_scopes_without_data_find_nothing_and_say_so(
        self, con: duckdb.DuckDBPyConnection, scope: str
    ) -> None:
        result = search(con, q="US0378331005", scope=scope)
        assert result["total"] == 0 and result["items"] == []
        assert scope.upper() in str(result["note"])

    def test_empty_scope_without_a_query_has_no_note(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert search(con, scope="isin")["note"] is None

    @pytest.mark.parametrize("q", ["", "   "])
    def test_blank_query_is_no_filter(
        self, con: duckdb.DuckDBPyConnection, q: str
    ) -> None:
        assert search(con, q=q)["total"] == 398

    def test_wildcards_in_the_query_are_literal(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert search(con, q="%", scope="name")["total"] == 0
        assert search(con, q="_", scope="name")["total"] == 0

    def test_sql_injection_text_is_just_text(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert search(con, q="'; DROP TABLE sec_instrument; --")["total"] == 0
        assert search(con)["total"] == 398

    @pytest.mark.parametrize("code, count", sorted(PRODUCT_COUNTS.items()))
    def test_product_code_filter(
        self, con: duckdb.DuckDBPyConnection, code: str, count: int
    ) -> None:
        result = search(con, product_code=code)
        assert result["total"] == count
        assert {item["product_code"] for item in result["items"]} == {code}  # type: ignore[union-attr]

    def test_unknown_product_code_is_empty_not_an_error(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert search(con, product_code="XX-YYY-ZZZ")["total"] == 0

    def test_venue_filter_is_case_insensitive(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert search(con, mic="xxxx")["total"] == 18

    def test_filters_combine(self, con: duckdb.DuckDBPyConnection) -> None:
        both = search(con, product_code="FI-BND-CONV", mic="XXXX")
        assert both["total"] < 94 and both["total"] == 18

    def test_sort_descending_reverses_ascending(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        asc = names(search(con, q="ACQUISITION", scope="name", sort="name"))
        desc = names(
            search(
                con,
                q="ACQUISITION",
                scope="name",
                sort="name",
                direction="desc",
            )
        )
        assert asc == sorted(asc) and desc == asc[::-1]

    def test_missing_values_sort_last(self, con: duckdb.DuckDBPyConnection) -> None:
        tickers = [item["ticker"] for item in search(con, sort="ticker")["items"]]  # type: ignore[union-attr]
        assert tickers[-1] is None and tickers[0] is not None


class TestGlobalIdentifierColumns:
    def test_an_exchange_listed_equity_carries_every_identifier_we_hold(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        row = search(con, q="02079K107")["items"][0]  # type: ignore[index]
        assert row["cusip"] == "02079K107" and row["cik"] == "0001652044"
        assert row["bbg_ticker"] == "GOOG" and row["ticker"] == "GOOG"
        assert row["figi"].startswith("BBG") and row["composite_figi"].startswith(
            "BBG"
        )  # share-class and composite FIGI

    def test_a_bond_has_no_composite_figi_and_only_a_bloomberg_description(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        row = search(con, q=MKS_CUSIP)["items"][0]  # type: ignore[index]
        assert row["composite_figi"] is None and row["ticker"] is None
        assert row["bbg_ticker"].startswith("MKSI ")

    def test_no_isin_or_sedol_is_reported_because_none_is_held(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert not {"isin", "sedol"} & set(search(con)["items"][0])  # type: ignore[arg-type,index]

    @pytest.mark.parametrize("sort", ["bbg_ticker", "composite_figi", "cik"])
    def test_sortable_by_each_identifier(
        self, con: duckdb.DuckDBPyConnection, sort: str
    ) -> None:
        values = [r[sort] for r in search(con, sort=sort)["items"]]  # type: ignore[union-attr,index]
        present = [v for v in values if v is not None]
        assert values[: len(present)] == present and present == sorted(present)


class TestUnderlyingColumn:
    def test_a_derived_security_names_its_underlying(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        row = search(con, q=MKS_CUSIP)["items"][0]  # type: ignore[index]
        assert row["underlying_name"] == "MKS INC"

    def test_an_underlying_has_none_of_its_own(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert search(con, q="MKSI", scope="ticker")["items"][0]["underlying_name"] is None  # type: ignore[index]

    def test_counts_match_the_stored_links(self, con: duckdb.DuckDBPyConnection) -> None:
        items = search(con)["items"]
        assert (
            len({r["instrument_id"] for r in items}) == 398
        )  # the join never duplicates a row  # type: ignore[union-attr,index]
        assert (
            sum(1 for r in items if r["underlying_name"]) == 184
        )  # 94 convertibles + 63 warrants + 27 rights  # type: ignore[union-attr,index]

    def test_sortable_with_missing_values_last(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        values = [r["underlying_name"] for r in search(con, sort="underlying")["items"]]  # type: ignore[union-attr,index]
        present = [v for v in values if v is not None]
        assert values[: len(present)] == present and present == sorted(present)


class TestUniverseFilters:
    def test_counts_cover_every_instrument(self, con: duckdb.DuckDBPyConnection) -> None:
        filters = service.universe_filters(con=con)
        assert {row["code"]: row["count"] for row in filters["product_codes"]} == PRODUCT_COUNTS  # type: ignore[union-attr]
        assert sum(row["count"] for row in filters["mics"]) == 398  # type: ignore[union-attr]
        assert filters["totals"] == {"instruments": 398, "exceptions": 22}

    def test_venue_counts_are_named(self, con: duckdb.DuckDBPyConnection) -> None:
        mics = {row["mic"]: row["count"] for row in service.universe_filters(con=con)["mics"]}  # type: ignore[union-attr]
        assert mics == {"XNAS": 249, "XOFF": 76, "XNYS": 52, "XXXX": 18, "XASE": 3}


class TestExceptionPage:
    def test_whole_queue_with_reason_counts(self, con: duckdb.DuckDBPyConnection) -> None:
        page = service.exception_page(con=con, search=ExceptionSearch())
        assert page["total"] == 22 and len(page["items"]) == 22  # type: ignore[arg-type]
        assert {row["reason_code"]: row["count"] for row in page["reasons"]} == {  # type: ignore[union-attr]
            "INVALID_IDENTIFIER": 13,
            "ISSUER_UNRESOLVED": 8,
            "VENUE_UNRESOLVED": 1,
        }

    def test_filter_by_reason(self, con: duckdb.DuckDBPyConnection) -> None:
        page = service.exception_page(
            con=con, search=ExceptionSearch(reason="ISSUER_UNRESOLVED")
        )
        assert page["total"] == 8
        assert {row["reason_code"] for row in page["items"]} == {"ISSUER_UNRESOLVED"}  # type: ignore[union-attr]

    def test_unknown_reason_is_empty(self, con: duckdb.DuckDBPyConnection) -> None:
        assert (
            service.exception_page(con=con, search=ExceptionSearch(reason="NOPE"))[
                "total"
            ]
            == 0
        )

    def test_rows_are_in_filing_order(self, con: duckdb.DuckDBPyConnection) -> None:
        page = service.exception_page(con=con, search=ExceptionSearch())
        rows = [row["row_number"] for row in page["items"]]  # type: ignore[union-attr]
        assert len(rows) == 22 and rows == sorted(rows)

    def test_a_queued_row_names_its_reason_in_words(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        items = service.exception_page(
            con=con, search=ExceptionSearch(reason="VENUE_UNRESOLVED")
        )["items"]
        assert "Nasdaq Trader" in str(items[0]["detail"])  # type: ignore[index]


class TestSecurityDetail:
    def test_convertible_bond(self, con: duckdb.DuckDBPyConnection) -> None:
        detail = service.security_detail(
            con=con, instrument_id=instrument_id(con, MKS_CUSIP)
        )
        assert detail["instrument"]["name"] == "MKS INC 1.25 06/01/2030"  # type: ignore[index]
        assert detail["taxonomy"]["asset_class_name"] == "Fixed Income"  # type: ignore[index]
        assert detail["taxonomy"]["base_product_name"] == "Bond"  # type: ignore[index]
        assert detail["terms"]["coupon_rate"] == 1.25 and detail["terms"]["maturity_date"] == "2030-06-01"  # type: ignore[index]
        assert detail["underlying"]["ticker"] == "MKSI" and detail["underlying"]["product_code"] == "EQ-SPT-COMMON"  # type: ignore[index]
        assert {row["scheme"] for row in detail["identifiers"]} == {"CUSIP", "FIGI"}  # type: ignore[union-attr]
        listing = detail["listings"][0]  # type: ignore[index]
        assert (listing["mic"], listing["confidence"], listing["source"]) == (
            "XOFF",
            "LOW",
            "DEFAULT",
        )
        assert listing["is_otc"] is True and listing["is_primary"] is True

    def test_terms_do_not_repeat_keys_shown_elsewhere(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        terms = service.security_detail(
            con=con, instrument_id=instrument_id(con, MKS_CUSIP)
        )["terms"]
        assert not {"instrument_id", "product_code", "underlying_instrument_id"} & set(terms)  # type: ignore[arg-type]

    def test_exchange_listed_equity_has_a_high_confidence_listing(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        detail = service.security_detail(
            con=con, instrument_id=instrument_id(con, "02079K107")
        )
        listing = detail["listings"][0]  # type: ignore[index]
        assert (listing["mic"], listing["symbol"], listing["confidence"]) == (
            "XNAS",
            "GOOG",
            "HIGH",
        )
        assert listing["is_otc"] is False
        assert detail["issuer"]["legal_name"] == "Alphabet Inc."  # type: ignore[index]

    def test_depositary_receipt_flags_its_unresolved_underlying(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        detail = service.security_detail(
            con=con, instrument_id=instrument_id(con, "948596101")
        )
        assert detail["terms"]["underlying_unresolved"] is True  # type: ignore[index]
        assert detail["underlying"] is None
        assert detail["issuer"]["country_code"] == "KY"  # type: ignore[index]

    def test_unit_needs_no_underlying(self, con: duckdb.DuckDBPyConnection) -> None:
        unit = search(con, product_code="EQ-SPT-UNIT")["items"][0]  # type: ignore[index]
        detail = service.security_detail(
            con=con, instrument_id=int(unit["instrument_id"])
        )
        assert detail["underlying"] is None
        assert "R3/R4" not in {check["rule"] for check in detail["governance"]["checks"]}  # type: ignore[index]

    def test_warrant_must_reference_an_underlying(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        warrant = search(con, product_code="EQ-SPT-WARRANT")["items"][0]  # type: ignore[index]
        detail = service.security_detail(
            con=con, instrument_id=int(warrant["instrument_id"])
        )
        assert detail["underlying"]["product_code"] == "EQ-SPT-COMMON"  # type: ignore[index]
        assert "R3/R4" in {check["rule"] for check in detail["governance"]["checks"]}  # type: ignore[index]

    def test_gaps_name_what_is_not_held(self, con: duckdb.DuckDBPyConnection) -> None:
        gaps = service.security_detail(con=con, instrument_id=instrument_id(con, MKS_CUSIP))["governance"]["gaps"]  # type: ignore[index]
        text = " ".join(gaps)
        for expected in (
            "ISIN",
            "SEDOL",
            "GICS",
            "SIC 3823",
            "LEI",
            "Currency",
            "Per-venue FIGI",
        ):
            assert expected in text

    def test_lineage_cites_the_filing_and_every_listing(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        lineage = service.security_detail(
            con=con, instrument_id=instrument_id(con, MKS_CUSIP)
        )["lineage"]
        sources = {row["source"] for row in lineage}  # type: ignore[union-attr]
        assert {
            "13F-HR:0001193125-26-350767",
            "OPENFIGI",
            "SEC_EDGAR",
            "DEFAULT",
        } <= sources

    def test_every_instrument_passes_its_integrity_checks(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        ids = [
            row[0]
            for row in con.execute("SELECT instrument_id FROM sec_instrument").fetchall()
        ]
        assert len(ids) == 398
        for each in ids:
            checks = service.security_detail(con=con, instrument_id=each)["governance"][
                "checks"
            ]
            failed = [check["rule"] for check in checks if not check["passed"]]  # type: ignore[union-attr]
            assert not failed, f"instrument {each} fails {failed}"

    @pytest.mark.parametrize("missing", [0, -1, 999_999])
    def test_unknown_instrument_raises_not_found(
        self, con: duckdb.DuckDBPyConnection, missing: int
    ) -> None:
        with pytest.raises(NotFoundError, match="No instrument"):
            service.security_detail(con=con, instrument_id=missing)


class TestIssuers:
    def test_every_issuer_is_returned_unpaged(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        page = service.issuer_page(con=con, search=IssuerSearch())
        assert page["total"] == 213 and len(page["items"]) == 213  # type: ignore[arg-type]
        assert sum(row["instruments"] for row in page["items"]) == 398  # type: ignore[union-attr]

    def test_row_shape(self, con: duckdb.DuckDBPyConnection) -> None:
        row = service.issuer_page(con=con, search=IssuerSearch(q="alphabet"))["items"][0]  # type: ignore[index]
        assert row["legal_name"] == "Alphabet Inc." and row["country"] == "US"
        assert row["cik"] == "0001652044" and row["instruments"] == 2

    def test_search_by_name_cik_and_cusip_prefix(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        for query in ("alphabet", "0001652044", "02079K"):
            items = service.issuer_page(con=con, search=IssuerSearch(q=query))["items"]
            assert [row["legal_name"] for row in items] == ["Alphabet Inc."], query  # type: ignore[union-attr]

    def test_wildcards_are_literal(self, con: duckdb.DuckDBPyConnection) -> None:
        assert service.issuer_page(con=con, search=IssuerSearch(q="%"))["total"] == 0

    def test_sort_by_instrument_count(self, con: duckdb.DuckDBPyConnection) -> None:
        counts = [row["instruments"] for row in service.issuer_page(con=con, search=IssuerSearch(sort="instruments", direction="desc"))["items"]]  # type: ignore[union-attr]
        assert counts == sorted(counts, reverse=True) and counts[0] > counts[-1]

    def test_detail_lists_the_issuers_instruments(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        issuer_id = service.issuer_page(con=con, search=IssuerSearch(q="alphabet"))["items"][0]["issuer_id"]  # type: ignore[index]
        detail = service.issuer_detail(con=con, issuer_id=int(issuer_id))
        assert detail["issuer"]["legal_name"] == "Alphabet Inc."  # type: ignore[index]
        assert sorted(row["ticker"] for row in detail["instruments"]) == ["GOOG", "GOOGL"]  # type: ignore[union-attr]

    @pytest.mark.parametrize("missing", [0, -5, 999_999])
    def test_unknown_issuer_raises_not_found(
        self, con: duckdb.DuckDBPyConnection, missing: int
    ) -> None:
        with pytest.raises(NotFoundError, match="No issuer"):
            service.issuer_detail(con=con, issuer_id=missing)
