"""Request models: defaults, bounds and rejected values."""

import pytest
from pydantic import ValidationError

from casm.api.v1.models import ExceptionSearch, IssuerSearch, SecuritySearch, VenueSearch


class TestSecuritySearch:
    def test_defaults(self) -> None:
        search = SecuritySearch()
        assert (search.scope, search.sort, search.direction) == ("all", "name", "asc")
        assert search.q is None

    @pytest.mark.parametrize("field", ["limit", "offset", "page"])
    def test_securities_are_never_paged(self, field: str) -> None:
        with pytest.raises(ValidationError):
            SecuritySearch(**{field: 5})

    @pytest.mark.parametrize(
        "field, value",
        [
            ("scope", "isn"),
            ("sort", "price"),
            ("direction", "up"),
            ("mic", "XNA"),
            ("mic", "XNASD"),
        ],
    )
    def test_invalid_choice_is_rejected(self, field: str, value: str) -> None:
        with pytest.raises(ValidationError):
            SecuritySearch(**{field: value})

    def test_sort_choices(self) -> None:
        assert SecuritySearch(sort="underlying").sort == "underlying"
        for bad in ("parent", "issuer"):
            with pytest.raises(ValidationError):
                SecuritySearch(sort=bad)

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SecuritySearch(color="red")

    def test_overlong_query_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SecuritySearch(q="x" * 101)


class TestExceptionSearch:
    def test_not_paged_and_reason_is_optional(self) -> None:
        assert ExceptionSearch().reason is None
        with pytest.raises(ValidationError):
            ExceptionSearch(limit=5)


class TestIssuerSearch:
    def test_defaults_and_rejections(self) -> None:
        search = IssuerSearch()
        assert (search.q, search.sort, search.direction) == (None, "name", "asc")
        for bad in (
            {"sort": "revenue"},
            {"direction": "up"},
            {"limit": 5},
            {"q": "x" * 101},
        ):
            with pytest.raises(ValidationError):
                IssuerSearch(**bad)


class TestVenueSearch:
    def test_defaults(self) -> None:
        search = VenueSearch()
        assert (search.loaded, search.sort) == (
            False,
            "mic",
        )  # the whole registry by default
        with pytest.raises(ValidationError):
            VenueSearch(limit=25)  # venues are never paged

    def test_venue_type_must_be_a_known_type(self) -> None:
        assert VenueSearch(venue_type="OTC").venue_type == "OTC"
        with pytest.raises(ValidationError):
            VenueSearch(venue_type="DARKPOOL")

    def test_country_must_be_two_letters(self) -> None:
        with pytest.raises(ValidationError):
            VenueSearch(country="USA")
