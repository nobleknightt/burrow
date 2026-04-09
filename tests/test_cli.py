"""Tests for CLI argument parsing."""

import pytest

from burrow.cli import build_parser


@pytest.fixture()
def parser():
    return build_parser()


class TestGlobalFlags:
    def test_default_profile(self, parser):
        args = parser.parse_args(["query", "SELECT 1"])
        assert args.profile == "default"

    def test_custom_profile(self, parser):
        args = parser.parse_args(["--profile", "staging", "query", "SELECT 1"])
        assert args.profile == "staging"

    def test_short_profile_flag(self, parser):
        args = parser.parse_args(["-p", "prod", "query", "SELECT 1"])
        assert args.profile == "prod"


class TestQueryCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["query", "SELECT 1"])
        assert args.command == "query"
        assert args.sql == "SELECT 1"
        assert args.output == "table"
        assert args.no_header is False

    def test_output_json(self, parser):
        args = parser.parse_args(["query", "SELECT 1", "--output", "json"])
        assert args.output == "json"

    def test_output_csv(self, parser):
        args = parser.parse_args(["query", "SELECT 1", "-o", "csv"])
        assert args.output == "csv"

    def test_no_header(self, parser):
        args = parser.parse_args(["query", "SELECT 1", "--no-header"])
        assert args.no_header is True

    def test_invalid_output_fails(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["query", "SELECT 1", "--output", "xml"])

    def test_missing_sql_fails(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["query"])


class TestDescribeCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["describe"])
        assert args.command == "describe"
        assert args.table is None

    def test_with_table(self, parser):
        args = parser.parse_args(["describe", "--table", "users"])
        assert args.table == "users"

    def test_short_table_flag(self, parser):
        args = parser.parse_args(["describe", "-t", "orders"])
        assert args.table == "orders"

    def test_with_schema(self, parser):
        args = parser.parse_args(["describe", "--schema", "myschema"])
        assert args.schema == "myschema"


class TestShellCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["shell"])
        assert args.command == "shell"


class TestConfigCommand:
    def test_set(self, parser):
        args = parser.parse_args(["config", "set"])
        assert args.command == "config"
        assert args.config_command == "set"

    def test_list(self, parser):
        args = parser.parse_args(["config", "list"])
        assert args.config_command == "list"

    def test_get(self, parser):
        args = parser.parse_args(["config", "get"])
        assert args.config_command == "get"
        assert args.key is None

    def test_get_with_key(self, parser):
        args = parser.parse_args(["config", "get", "ssh_host"])
        assert args.key == "ssh_host"

    def test_unset(self, parser):
        args = parser.parse_args(["config", "unset", "staging"])
        assert args.config_command == "unset"
        assert args.profile_name == "staging"

    def test_missing_subcommand_fails(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["config"])


class TestMissingCommand:
    def test_no_command_fails(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args([])
