"""LIKE escaping for user text."""

import duckdb

from casm.api.utils.sql_utils import contains, prefix


class TestSqlUtils:
    def test_contains_wraps_text(self) -> None:
        assert contains(text="mks") == "%mks%"

    def test_wildcards_are_escaped_so_they_match_literally(self) -> None:
        assert contains(text="50%_off\\") == "%50\\%\\_off\\\\%"

    def test_prefix_has_no_leading_wildcard(self) -> None:
        assert prefix(text="55306") == "55306%"

    def test_escaped_text_matches_literally_in_duckdb(self) -> None:
        con: duckdb.DuckDBPyConnection = duckdb.connect()
        sql: str = (
            "SELECT count(*) FROM (VALUES ('a%b'), ('aXb')) t(v) WHERE v LIKE ? ESCAPE '\\'"
        )
        assert con.execute(sql, [contains(text="a%b")]).fetchone() == (1,)
