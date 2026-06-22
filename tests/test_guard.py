"""Tests for the SQL access-mode guard."""

import pytest

from burrow.commands.query import check_access, statement_keyword
from burrow.config import AccessMode


class TestStatementKeyword:
    def test_simple_select(self):
        assert statement_keyword("SELECT * FROM users") == "SELECT"

    def test_case_insensitive(self):
        assert statement_keyword("select * from users") == "SELECT"

    def test_insert(self):
        assert statement_keyword("INSERT INTO users VALUES (1)") == "INSERT"

    def test_update(self):
        assert statement_keyword("UPDATE users SET name = 'x'") == "UPDATE"

    def test_delete(self):
        assert statement_keyword("DELETE FROM users WHERE id = 1") == "DELETE"

    def test_truncate(self):
        assert statement_keyword("TRUNCATE TABLE users") == "TRUNCATE"

    def test_create(self):
        assert statement_keyword("CREATE TABLE foo (id INT)") == "CREATE"

    def test_drop(self):
        assert statement_keyword("DROP TABLE foo") == "DROP"

    def test_alter(self):
        assert statement_keyword("ALTER TABLE foo ADD COLUMN bar INT") == "ALTER"

    def test_replace(self):
        assert statement_keyword("REPLACE INTO users VALUES (1, 'x')") == "REPLACE"

    def test_merge(self):
        assert statement_keyword("MERGE INTO target USING source ON ...") == "MERGE"

    def test_rename(self):
        assert statement_keyword("RENAME TABLE old TO new") == "RENAME"

    def test_copy(self):
        assert statement_keyword("COPY users FROM '/tmp/data.csv'") == "COPY"

    def test_load(self):
        assert statement_keyword("LOAD DATA INFILE '/tmp/data.csv' INTO TABLE users") == "LOAD"

    def test_leading_whitespace(self):
        assert statement_keyword("   SELECT 1") == "SELECT"

    def test_line_comment_stripped(self):
        assert statement_keyword("-- find users\nSELECT * FROM users") == "SELECT"

    def test_block_comment_stripped(self):
        assert statement_keyword("/* admin query */ DELETE FROM users") == "DELETE"

    def test_empty_after_strip(self):
        assert statement_keyword("-- just a comment") is None

    def test_empty_string(self):
        assert statement_keyword("") is None

    def test_cte_select(self):
        sql = "WITH cte AS (SELECT id FROM users) SELECT * FROM cte"
        assert statement_keyword(sql) == "SELECT"

    def test_cte_insert(self):
        sql = "WITH src AS (SELECT id FROM staging) INSERT INTO users SELECT * FROM src"
        assert statement_keyword(sql) == "INSERT"

    def test_cte_update(self):
        sql = "WITH ids AS (SELECT id FROM tmp) UPDATE users SET active = false WHERE id IN (SELECT id FROM ids)"
        assert statement_keyword(sql) == "UPDATE"

    def test_multiple_ctes(self):
        sql = (
            "WITH a AS (SELECT 1), b AS (SELECT 2) "
            "DELETE FROM users WHERE id IN (SELECT * FROM a)"
        )
        assert statement_keyword(sql) == "DELETE"


class TestCheckAccess:
    def test_readwrite_allows_select(self):
        check_access("SELECT 1", AccessMode.READWRITE)  # no exception

    def test_readwrite_allows_insert(self):
        check_access("INSERT INTO t VALUES (1)", AccessMode.READWRITE)  # no exception

    def test_readwrite_allows_drop(self):
        check_access("DROP TABLE t", AccessMode.READWRITE)  # no exception

    def test_read_allows_select(self):
        check_access("SELECT * FROM users", AccessMode.READ)  # no exception

    def test_read_allows_explain(self):
        check_access("EXPLAIN SELECT * FROM users", AccessMode.READ)  # no exception

    def test_read_blocks_insert(self):
        with pytest.raises(SystemExit, match="INSERT"):
            check_access("INSERT INTO users VALUES (1)", AccessMode.READ)

    def test_read_blocks_update(self):
        with pytest.raises(SystemExit, match="UPDATE"):
            check_access("UPDATE users SET name = 'x'", AccessMode.READ)

    def test_read_blocks_delete(self):
        with pytest.raises(SystemExit, match="DELETE"):
            check_access("DELETE FROM users", AccessMode.READ)

    def test_read_blocks_truncate(self):
        with pytest.raises(SystemExit, match="TRUNCATE"):
            check_access("TRUNCATE TABLE users", AccessMode.READ)

    def test_read_blocks_drop(self):
        with pytest.raises(SystemExit, match="DROP"):
            check_access("DROP TABLE users", AccessMode.READ)

    def test_read_blocks_create(self):
        with pytest.raises(SystemExit, match="CREATE"):
            check_access("CREATE TABLE foo (id INT)", AccessMode.READ)

    def test_read_blocks_alter(self):
        with pytest.raises(SystemExit, match="ALTER"):
            check_access("ALTER TABLE foo ADD COLUMN x INT", AccessMode.READ)

    def test_read_blocks_replace(self):
        with pytest.raises(SystemExit, match="REPLACE"):
            check_access("REPLACE INTO users VALUES (1)", AccessMode.READ)

    def test_read_blocks_copy(self):
        with pytest.raises(SystemExit, match="COPY"):
            check_access("COPY users FROM '/tmp/data.csv'", AccessMode.READ)

    def test_read_blocks_load(self):
        with pytest.raises(SystemExit, match="LOAD"):
            check_access("LOAD DATA INFILE '/tmp/data.csv' INTO TABLE users", AccessMode.READ)

    def test_read_blocks_cte_insert(self):
        sql = "WITH src AS (SELECT id FROM staging) INSERT INTO users SELECT * FROM src"
        with pytest.raises(SystemExit, match="INSERT"):
            check_access(sql, AccessMode.READ)

    def test_error_message_mentions_profile_setting(self):
        with pytest.raises(SystemExit) as exc:
            check_access("DELETE FROM users", AccessMode.READ)
        assert "access_mode = readwrite" in str(exc.value)
