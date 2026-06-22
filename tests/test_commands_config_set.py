"""Tests for burrow config set <key> <value> (single-field update)."""

import tomllib
from types import SimpleNamespace

import pytest

import burrow.commands.config as cmd_cfg_mod
import burrow.config
from burrow.commands.config import _cmd_set_field
from burrow.config import AccessMode, DBType


def make_args(key, value=None, profile="default"):
    return SimpleNamespace(key=key, value=value, profile=profile)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point config file and profiles dir at a fresh temp location."""
    config_file = tmp_path / "config.toml"
    profiles_dir = tmp_path / "profiles"
    monkeypatch.setenv("BURROW_CONFIG", str(config_file))
    monkeypatch.setattr(burrow.config, "PROFILES_DIR", profiles_dir)
    monkeypatch.setattr(cmd_cfg_mod, "PROFILES_DIR", profiles_dir)
    return config_file


class TestSetStringField:
    def test_sets_db_host(self, isolated_config):
        _cmd_set_field(make_args("db_host", "newhost.example.com"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["db_host"] == "newhost.example.com"

    def test_sets_ssh_host(self, isolated_config):
        _cmd_set_field(make_args("ssh_host", "ssh.example.com"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["ssh_host"] == "ssh.example.com"

    def test_sets_ssh_user(self, isolated_config):
        _cmd_set_field(make_args("ssh_user", "deploy"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["ssh_user"] == "deploy"

    def test_creates_profile_section_if_missing(self, isolated_config):
        _cmd_set_field(make_args("db_name", "appdb", profile="staging"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["staging"]["db_name"] == "appdb"

    def test_preserves_other_fields(self, isolated_config):
        isolated_config.write_text('[default]\ndb_host = "old.example.com"\ndb_name = "appdb"\n')
        _cmd_set_field(make_args("db_host", "new.example.com"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["db_host"] == "new.example.com"
        assert data["default"]["db_name"] == "appdb"


class TestSetIntField:
    def test_sets_db_port(self, isolated_config):
        _cmd_set_field(make_args("db_port", "5433"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["db_port"] == 5433

    def test_sets_ssh_port(self, isolated_config):
        _cmd_set_field(make_args("ssh_port", "2222"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["ssh_port"] == 2222

    def test_invalid_int_exits(self):
        with pytest.raises(SystemExit):
            _cmd_set_field(make_args("db_port", "notanumber"))


class TestSetBoolField:
    def test_sets_use_ssh_false(self, isolated_config):
        _cmd_set_field(make_args("use_ssh", "false"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["use_ssh"] is False

    def test_sets_use_ssh_true(self, isolated_config):
        _cmd_set_field(make_args("use_ssh", "true"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["use_ssh"] is True

    def test_falsy_variants(self, isolated_config):
        for falsy in ("false", "0", "no", "off"):
            _cmd_set_field(make_args("use_ssh", falsy))
            data = tomllib.loads(isolated_config.read_text())
            assert data["default"]["use_ssh"] is False, f"expected False for '{falsy}'"


class TestSetEnumField:
    def test_sets_access_mode_read(self, isolated_config):
        _cmd_set_field(make_args("access_mode", "read"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["access_mode"] == "read"

    def test_sets_access_mode_readwrite(self, isolated_config):
        _cmd_set_field(make_args("access_mode", "readwrite"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["access_mode"] == "readwrite"

    def test_sets_db_type_mysql(self, isolated_config):
        _cmd_set_field(make_args("db_type", "mysql"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["db_type"] == "mysql"

    def test_invalid_access_mode_exits(self):
        with pytest.raises(SystemExit):
            _cmd_set_field(make_args("access_mode", "superadmin"))

    def test_invalid_db_type_exits(self):
        with pytest.raises(SystemExit):
            _cmd_set_field(make_args("db_type", "oracle"))

    def test_case_insensitive(self, isolated_config):
        _cmd_set_field(make_args("access_mode", "READ"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["default"]["access_mode"] == "read"


class TestSetPassword:
    def test_writes_password_file(self, tmp_path, isolated_config):
        _cmd_set_field(make_args("db_password", "newsecret"))
        pw_file = tmp_path / "profiles" / "default.password"
        assert pw_file.exists()
        assert pw_file.read_text() == "newsecret"

    def test_password_not_written_to_toml(self, tmp_path, isolated_config):
        _cmd_set_field(make_args("db_password", "secret"))
        data = tomllib.loads(isolated_config.read_text()) if isolated_config.exists() else {}
        assert "db_password" not in data.get("default", {})

    def test_missing_password_value_exits(self, monkeypatch):
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "")
        with pytest.raises(SystemExit):
            _cmd_set_field(make_args("db_password", None))


class TestSetErrors:
    def test_unknown_key_exits(self):
        with pytest.raises(SystemExit):
            _cmd_set_field(make_args("nonexistent_key", "value"))

    def test_missing_value_exits(self):
        with pytest.raises(SystemExit):
            _cmd_set_field(make_args("db_host", None))

    def test_named_profile(self, isolated_config):
        _cmd_set_field(make_args("db_port", "3306", profile="prod"))
        data = tomllib.loads(isolated_config.read_text())
        assert data["prod"]["db_port"] == 3306
