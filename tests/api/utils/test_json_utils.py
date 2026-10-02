"""JSON conversion of database values."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from casm.api.utils.json_utils import plain_value


class TestPlainValue:
    def test_fractional_decimal_becomes_float(self) -> None:
        assert plain_value(Decimal("1.250")) == 1.25
        assert isinstance(plain_value(Decimal("1.250")), float)

    def test_whole_decimal_becomes_int(self) -> None:
        value: object = plain_value(Decimal("100.000"))
        assert value == 100 and isinstance(value, int)

    def test_dates_become_iso_text(self) -> None:
        assert plain_value(date(2030, 6, 1)) == "2030-06-01"
        assert plain_value(datetime(2026, 9, 30, 12, 30)) == "2026-09-30T12:30:00"

    @pytest.mark.parametrize("value", [None, "text", 7, True, 2.5])
    def test_other_values_pass_through(self, value: object) -> None:
        assert plain_value(value) is value
