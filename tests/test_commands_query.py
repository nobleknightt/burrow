"""Tests for the query command (tunnel mocked)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from burrow.commands.query import cmd_query


def make_args(sql, output="table", no_header=False, profile="default"):
    return SimpleNamespace(sql=sql, output=output, no_header=no_header, profile=profile)


def make_tunnel(columns, rows):
    """Return a mocked PostgresSSHTunnel context manager."""
    description = [SimpleNamespace(name=col) for col in columns]
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.description = description
    cur.fetchall.return_value = rows

    conn = MagicMock()
    conn.cursor.return_value = cur

    tunnel = MagicMock()
    tunnel.__enter__ = lambda s: s
    tunnel.__exit__ = MagicMock(return_value=False)
    tunnel.get_connection.return_value = conn

    return tunnel


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    cfg = MagicMock()
    monkeypatch.setattr(
        "burrow.commands.query.load_config", lambda profile="default": cfg
    )


class TestCmdQuery:
    def test_table_output(self, capsys):
        tunnel = make_tunnel(["id", "name"], [(1, "alice"), (2, "bob")])
        with patch("burrow.commands.query.PostgresSSHTunnel", return_value=tunnel):
            cmd_query(make_args("SELECT 1"))

        out = capsys.readouterr().out
        assert "alice" in out
        assert "bob" in out

    def test_json_output(self, capsys):
        import json

        tunnel = make_tunnel(["id", "name"], [(1, "alice")])
        with patch("burrow.commands.query.PostgresSSHTunnel", return_value=tunnel):
            cmd_query(make_args("SELECT 1", output="json"))

        data = json.loads(capsys.readouterr().out)
        assert data == [{"id": 1, "name": "alice"}]

    def test_csv_output(self, capsys):
        tunnel = make_tunnel(["id", "name"], [(1, "alice")])
        with patch("burrow.commands.query.PostgresSSHTunnel", return_value=tunnel):
            cmd_query(make_args("SELECT 1", output="csv"))

        lines = capsys.readouterr().out.strip().splitlines()
        assert lines[0] == "id,name"
        assert lines[1] == "1,alice"

    def test_no_header(self, capsys):
        tunnel = make_tunnel(["id", "name"], [(1, "alice")])
        with patch("burrow.commands.query.PostgresSSHTunnel", return_value=tunnel):
            cmd_query(make_args("SELECT 1", output="csv", no_header=True))

        lines = capsys.readouterr().out.strip().splitlines()
        assert lines[0] == "1,alice"

    def test_no_rows_prints_to_stderr(self, capsys):
        tunnel = make_tunnel(["id"], [])
        with patch("burrow.commands.query.PostgresSSHTunnel", return_value=tunnel):
            cmd_query(make_args("SELECT 1"))

        assert "(no rows)" in capsys.readouterr().err

    def test_dml_prints_rowcount(self, capsys):
        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        cur.description = None
        cur.rowcount = 3

        conn = MagicMock()
        conn.cursor.return_value = cur

        tunnel = MagicMock()
        tunnel.__enter__ = lambda s: s
        tunnel.__exit__ = MagicMock(return_value=False)
        tunnel.get_connection.return_value = conn

        with patch("burrow.commands.query.PostgresSSHTunnel", return_value=tunnel):
            cmd_query(make_args("DELETE FROM foo"))

        assert "3 row(s) affected" in capsys.readouterr().out
