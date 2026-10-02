"""Row fetching helpers."""

import duckdb
import pytest

from casm.api.utils.database_utils import fetch_all, fetch_one, scalar


class TestDatabaseUtils:
    @pytest.fixture
    def con(self) -> duckdb.DuckDBPyConnection:
        connection: duckdb.DuckDBPyConnection = duckdb.connect()
        connection.execute(
            "CREATE TABLE t (id INTEGER, price NUMERIC(10, 3), d DATE); "
            "INSERT INTO t VALUES (1, 1.250, DATE '2030-06-01'), (2, 100.000, NULL)"
        )
        return connection

    def test_fetch_all_gives_dictionaries_of_plain_values(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert fetch_all(con=con, sql="SELECT * FROM t ORDER BY id") == [
            {"id": 1, "price": 1.25, "d": "2030-06-01"},
            {"id": 2, "price": 100, "d": None},
        ]

    def test_parameters_are_bound_not_interpolated(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        rows = fetch_all(con=con, sql="SELECT id FROM t WHERE id = ?", params=[1])
        assert rows == [{"id": 1}]
        assert (
            fetch_all(
                con=con,
                sql="SELECT id FROM t WHERE CAST(id AS VARCHAR) = ?",
                params=["1 OR 1=1"],
            )
            == []
        )

    def test_fetch_one_returns_first_row_or_none(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        assert fetch_one(con=con, sql="SELECT id FROM t ORDER BY id") == {"id": 1}
        assert fetch_one(con=con, sql="SELECT id FROM t WHERE id = 99") is None

    def test_scalar_counts(self, con: duckdb.DuckDBPyConnection) -> None:
        assert scalar(con=con, sql="SELECT count(*) FROM t") == 2
