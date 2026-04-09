"""Tests for output formatting."""

import datetime
import decimal
import json

import pytest

from burrow.output import format_csv, format_json, format_table


COLUMNS = ["id", "name", "active"]
ROWS = [(1, "alice", True), (2, "bob", False)]


class TestFormatTable:
    def test_basic(self):
        out = format_table(ROWS, COLUMNS)
        assert "id" in out
        assert "name" in out
        assert "alice" in out
        assert "bob" in out

    def test_no_header(self):
        out = format_table(ROWS, COLUMNS, no_header=True)
        assert "id" not in out
        assert "alice" in out

    def test_single_row(self):
        out = format_table([(42, "carol", True)], COLUMNS)
        assert "carol" in out


class TestFormatJson:
    def test_basic(self):
        out = format_json(ROWS, COLUMNS)
        data = json.loads(out)
        assert len(data) == 2
        assert data[0] == {"id": 1, "name": "alice", "active": True}
        assert data[1] == {"id": 2, "name": "bob", "active": False}

    def test_datetime_serialised(self):
        rows = [(datetime.date(2024, 1, 15),)]
        out = format_json(rows, ["dt"])
        data = json.loads(out)
        assert data[0]["dt"] == "2024-01-15"

    def test_decimal_serialised(self):
        rows = [(decimal.Decimal("3.14"),)]
        out = format_json(rows, ["price"])
        data = json.loads(out)
        assert data[0]["price"] == pytest.approx(3.14)

    def test_fallback_serialiser(self):
        class Custom:
            def __str__(self):
                return "custom"

        rows = [(Custom(),)]
        out = format_json(rows, ["val"])
        data = json.loads(out)
        assert data[0]["val"] == "custom"

    def test_empty(self):
        out = format_json([], COLUMNS)
        assert json.loads(out) == []


class TestFormatCsv:
    def test_basic(self):
        out = format_csv(ROWS, COLUMNS)
        lines = out.splitlines()
        assert lines[0] == "id,name,active"
        assert lines[1] == "1,alice,True"

    def test_no_header(self):
        out = format_csv(ROWS, COLUMNS, no_header=True)
        lines = out.splitlines()
        assert lines[0] == "1,alice,True"

    def test_quoting(self):
        rows = [("hello, world",)]
        out = format_csv(rows, ["val"])
        assert '"hello, world"' in out
