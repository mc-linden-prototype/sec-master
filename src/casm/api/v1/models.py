"""Validated request models for the API, bound to each route's query string. No grid is ever paged."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchScope = Literal["all", "isin", "cusip", "sedol", "figi", "ticker", "name"]
SecuritySort = Literal[
    "name",
    "product_code",
    "ticker",
    "mic",
    "cusip",
    "figi",
    "country",
    "confidence",
    "underlying",
    "bbg_ticker",
    "composite_figi",
    "cik",
]
VenueSort = Literal[
    "mic", "operating_mic", "name", "country", "type", "status", "listings"
]
VenueType = Literal["EXCHANGE", "MTF", "OTF", "SI", "OTC", "NONE"]
Direction = Literal["asc", "desc"]


class SecuritySearch(BaseModel):
    """Search, filter and sort the instrument universe. Never paged: every match is returned."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=100)
    scope: SearchScope = "all"
    product_code: str | None = None
    mic: str | None = Field(default=None, min_length=4, max_length=4)
    sort: SecuritySort = "name"
    direction: Direction = "asc"


IssuerSort = Literal["name", "type", "country", "cik", "instruments"]


class IssuerSearch(BaseModel):
    """Search and sort the issuers. Never paged."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=100)
    sort: IssuerSort = "name"
    direction: Direction = "asc"


class ExceptionSearch(BaseModel):
    """Filter the exception queue by reason code. Never paged."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class VenueSearch(BaseModel):
    """Search, filter and sort venues. By default the whole ISO 10383 registry; `loaded=true` narrows it to the
    venues loaded into CASM."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    venue_type: VenueType | None = None
    status: str | None = None
    loaded: bool = False
    sort: VenueSort = "mic"
    direction: Direction = "asc"
