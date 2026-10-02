"""Turns database values into plain JSON-friendly Python values."""

from datetime import date, datetime
from decimal import Decimal


def plain_value(value: object) -> object:
    """Convert a DuckDB value for JSON: Decimal to int or float, dates to ISO text, rest unchanged.

    A Decimal with no fractional part becomes an int (a lot size of 100, not 100.0).
    """
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value
