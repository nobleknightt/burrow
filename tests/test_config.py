"""Tests for configuration resolution."""

import os

import pytest

from burrow.config import load_config, list_profiles


REQUIRED = {
    "BURROW_SSH_HOST": "bastion.example.com",
    "BURROW_SSH_KEY_PATH": "~/.ssh/id_rsa",
    "BURROW_DB_HOST": "db.example.com",
    "BURROW_DB_USER": "myuser",
    "BURROW_DB_PASSWORD": "secret",
    "BURROW_DB_NAME": "mydb",
}


@pytest.fixture(autouse=True)
def clear_burrow_env(monkeypatch):
    """Remove any real BURROW_* env vars so they don't bleed into tests."""
    for key in list(os.environ):
        if key.startswith("BURROW_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def env(monkeypatch):
    """Set all required env vars."""
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)


class TestLoadConfigFromEnv:
    def test_required_fields(self, env):
        cfg = load_config()
        assert cfg.ssh_host == "bastion.example.com"
        assert cfg.db_user == "myuser"
        assert cfg.db_name == "mydb"

    def test_defaults_applied(self, env):
        cfg = load_config()
        assert cfg.ssh_user == "ec2-user"
        assert cfg.ssh_port == 22
        assert cfg.db_port == 5432
        assert cfg.db_schema == "public"
        assert cfg.connection_timeout == 10

    def test_int_fields_coerced(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_SSH_PORT", "2222")
        monkeypatch.setenv("BURROW_DB_PORT", "5433")
        cfg = load_config()
        assert cfg.ssh_port == 2222
        assert cfg.db_port == 5433

    def test_override_defaults(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_SSH_USER", "admin")
        monkeypatch.setenv("BURROW_DB_SCHEMA", "myschema")
        cfg = load_config()
        assert cfg.ssh_user == "admin"
        assert cfg.db_schema == "myschema"

    def test_missing_required_exits(self, monkeypatch):
        with pytest.raises(SystemExit):
            load_config()

    def test_missing_one_required_exits(self, env, monkeypatch):
        monkeypatch.delenv("BURROW_DB_PASSWORD")
        with pytest.raises(SystemExit):
            load_config()


class TestLoadConfigFromFile:
    def test_reads_default_profile(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            'ssh_host     = "bastion.example.com"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host     = "db.example.com"\n'
            'db_user      = "myuser"\n'
            'db_password  = "secret"\n'
            'db_name      = "mydb"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        cfg = load_config()
        assert cfg.ssh_host == "bastion.example.com"
        assert cfg.db_name == "mydb"

    def test_reads_named_profile(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            'ssh_host     = "bastion.example.com"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host     = "db.example.com"\n'
            'db_user      = "myuser"\n'
            'db_password  = "secret"\n'
            'db_name      = "mydb"\n'
            "\n"
            "[staging]\n"
            'ssh_host     = "bastion-staging.example.com"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host     = "db-staging.example.com"\n'
            'db_user      = "myuser"\n'
            'db_password  = "secret"\n'
            'db_name      = "mydb_staging"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        cfg = load_config(profile="staging")
        assert cfg.ssh_host == "bastion-staging.example.com"
        assert cfg.db_name == "mydb_staging"

    def test_missing_profile_exits(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[default]\n")
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        with pytest.raises(SystemExit):
            load_config(profile="nonexistent")

    def test_missing_file_falls_through_to_missing_required(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("BURROW_CONFIG", str(tmp_path / "nonexistent.toml"))
        with pytest.raises(SystemExit):
            load_config()

    def test_env_wins_over_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            'ssh_host     = "file-bastion.example.com"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host     = "db.example.com"\n'
            'db_user      = "myuser"\n'
            'db_password  = "secret"\n'
            'db_name      = "mydb"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        monkeypatch.setenv("BURROW_SSH_HOST", "env-bastion.example.com")
        cfg = load_config()
        assert cfg.ssh_host == "env-bastion.example.com"


class TestListProfiles:
    def test_returns_profiles(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[default]\n\n[staging]\n\n[prod]\n")
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        assert list_profiles() == ["default", "staging", "prod"]

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BURROW_CONFIG", str(tmp_path / "nonexistent.toml"))
        assert list_profiles() == []


class TestDatabaseConfig:
    def test_expands_tilde_in_key_path(self, env):
        cfg = load_config()
        assert "~" not in cfg.ssh_key_path
