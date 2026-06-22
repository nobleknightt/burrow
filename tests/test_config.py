"""Tests for configuration resolution."""

import os

import pytest

import burrow.config
from burrow.config import AccessMode, load_config, list_profiles


REQUIRED = {
    "BURROW_SSH_HOST": "ssh.example.com",
    "BURROW_SSH_USER": "sshuser",
    "BURROW_SSH_KEY_PATH": "~/.ssh/id_rsa",
    "BURROW_DB_HOST": "db.example.com",
    "BURROW_DB_PORT": "5432",
    "BURROW_DB_USER": "appuser",
    "BURROW_DB_PASSWORD": "secret",
    "BURROW_DB_NAME": "appdb",
}


@pytest.fixture(autouse=True)
def clear_burrow_env(monkeypatch):
    """Remove any real BURROW_* env vars so they don't bleed into tests."""
    for key in list(os.environ):
        if key.startswith("BURROW_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def isolated_profiles_dir(tmp_path, monkeypatch):
    """Point PROFILES_DIR at a fresh temp dir so password files don't bleed."""
    monkeypatch.setattr(burrow.config, "PROFILES_DIR", tmp_path / "profiles")


@pytest.fixture()
def env(monkeypatch):
    """Set all required env vars (including BURROW_DB_PASSWORD)."""
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)


class TestLoadConfigFromEnv:
    def test_required_fields(self, env):
        cfg = load_config()
        assert cfg.ssh_host == "ssh.example.com"
        assert cfg.db_user == "appuser"
        assert cfg.db_name == "appdb"

    def test_defaults_applied(self, env):
        cfg = load_config()
        assert cfg.ssh_port == 22
        assert cfg.db_port == 5432
        assert cfg.db_schema == "public"
        assert cfg.connection_timeout == 10

    def test_db_type_defaults_to_postgres(self, env):
        cfg = load_config()
        assert cfg.db_type == "postgres"

    def test_int_fields_coerced(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_SSH_PORT", "2222")
        monkeypatch.setenv("BURROW_DB_PORT", "5433")
        cfg = load_config()
        assert cfg.ssh_port == 2222
        assert cfg.db_port == 5433

    def test_override_defaults(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_SSH_USER", "admin")
        monkeypatch.setenv("BURROW_DB_SCHEMA", "appschema")
        cfg = load_config()
        assert cfg.ssh_user == "admin"
        assert cfg.db_schema == "appschema"

    def test_missing_required_exits(self, monkeypatch):
        with pytest.raises(SystemExit):
            load_config()

    def test_missing_one_required_exits(self, env, monkeypatch):
        monkeypatch.delenv("BURROW_DB_PASSWORD")
        with pytest.raises(SystemExit):
            load_config()


class TestPasswordResolution:
    def test_password_from_env(self, env):
        cfg = load_config()
        assert cfg.db_password == "secret"

    def test_password_from_file(self, tmp_path, monkeypatch):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "default.password").write_text("filepassword")
        monkeypatch.setattr(burrow.config, "PROFILES_DIR", profiles_dir)

        for k, v in {
            "BURROW_SSH_HOST": "ssh.example.com",
            "BURROW_SSH_USER": "sshuser",
            "BURROW_SSH_KEY_PATH": "~/.ssh/id_rsa",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_PORT": "5432",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)

        cfg = load_config()
        assert cfg.db_password == "filepassword"

    def test_env_wins_over_file(self, tmp_path, monkeypatch):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "default.password").write_text("filepassword")
        monkeypatch.setattr(burrow.config, "PROFILES_DIR", profiles_dir)

        for k, v in {
            "BURROW_SSH_HOST": "ssh.example.com",
            "BURROW_SSH_USER": "sshuser",
            "BURROW_SSH_KEY_PATH": "~/.ssh/id_rsa",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_PORT": "5432",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_NAME": "appdb",
            "BURROW_DB_PASSWORD": "envpassword",
        }.items():
            monkeypatch.setenv(k, v)

        cfg = load_config()
        assert cfg.db_password == "envpassword"

    def test_password_file_strips_whitespace(self, tmp_path, monkeypatch):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "default.password").write_text("  mypassword\n")
        monkeypatch.setattr(burrow.config, "PROFILES_DIR", profiles_dir)

        for k, v in {
            "BURROW_SSH_HOST": "ssh.example.com",
            "BURROW_SSH_USER": "sshuser",
            "BURROW_SSH_KEY_PATH": "~/.ssh/id_rsa",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_PORT": "5432",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)

        cfg = load_config()
        assert cfg.db_password == "mypassword"


class TestDbType:
    def test_mysql_uses_port_3306_by_default(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_TYPE": "mysql",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        cfg = load_config()
        assert cfg.db_type == "mysql"
        assert cfg.db_port == 3306

    def test_postgres_uses_port_5432_by_default(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        cfg = load_config()
        assert cfg.db_type == "postgres"
        assert cfg.db_port == 5432

    def test_explicit_port_overrides_type_default(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_TYPE": "mysql",
            "BURROW_DB_PORT": "3307",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        cfg = load_config()
        assert cfg.db_port == 3307

    def test_invalid_db_type_exits(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_TYPE": "oracle",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        with pytest.raises(SystemExit):
            load_config()

    def test_db_type_enum_returned(self, monkeypatch):
        from burrow.config import DBType
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_TYPE": "mysql",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        cfg = load_config()
        assert cfg.db_type is DBType.MYSQL


class TestAccessMode:
    def test_default_is_readwrite(self, env):
        cfg = load_config()
        assert cfg.access_mode == AccessMode.READWRITE

    def test_env_sets_read(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_ACCESS_MODE", "read")
        cfg = load_config()
        assert cfg.access_mode == AccessMode.READ

    def test_env_sets_readwrite_explicitly(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_ACCESS_MODE", "readwrite")
        cfg = load_config()
        assert cfg.access_mode == AccessMode.READWRITE

    def test_invalid_access_mode_exits(self, env, monkeypatch):
        monkeypatch.setenv("BURROW_ACCESS_MODE", "superadmin")
        with pytest.raises(SystemExit):
            load_config()

    def test_access_mode_from_config_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            'ssh_host     = "ssh.example.com"\n'
            'ssh_user     = "sshuser"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host      = "db.example.com"\n'
            'db_port      = 5432\n'
            'db_user      = "appuser"\n'
            'db_name      = "appdb"\n'
            'access_mode  = "read"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        monkeypatch.setenv("BURROW_DB_PASSWORD", "secret")
        cfg = load_config()
        assert cfg.access_mode == AccessMode.READ


class TestLoadConfigFromFile:
    def test_reads_default_profile(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            'ssh_host     = "ssh.example.com"\n'
            'ssh_user     = "sshuser"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host      = "db.example.com"\n'
            'db_port      = 5432\n'
            'db_user      = "appuser"\n'
            'db_name      = "appdb"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        monkeypatch.setenv("BURROW_DB_PASSWORD", "secret")
        cfg = load_config()
        assert cfg.ssh_host == "ssh.example.com"
        assert cfg.db_name == "appdb"

    def test_reads_named_profile(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            'ssh_host     = "ssh.example.com"\n'
            'ssh_user     = "sshuser"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host      = "db.example.com"\n'
            'db_port      = 5432\n'
            'db_user      = "appuser"\n'
            'db_name      = "appdb"\n'
            "\n"
            "[staging]\n"
            'ssh_host     = "ssh-staging.example.com"\n'
            'ssh_user     = "sshuser"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host      = "db-staging.example.com"\n'
            'db_port      = 5432\n'
            'db_user      = "appuser"\n'
            'db_name      = "appdb_staging"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        monkeypatch.setenv("BURROW_DB_PASSWORD", "secret")
        cfg = load_config(profile="staging")
        assert cfg.ssh_host == "ssh-staging.example.com"
        assert cfg.db_name == "appdb_staging"

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
            'ssh_host     = "file-ssh.example.com"\n'
            'ssh_user     = "sshuser"\n'
            'ssh_key_path = "~/.ssh/id_rsa"\n'
            'db_host      = "db.example.com"\n'
            'db_port      = 5432\n'
            'db_user      = "appuser"\n'
            'db_name      = "appdb"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        monkeypatch.setenv("BURROW_DB_PASSWORD", "secret")
        monkeypatch.setenv("BURROW_SSH_HOST", "env-ssh.example.com")
        cfg = load_config()
        assert cfg.ssh_host == "env-ssh.example.com"


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

    def test_ssh_key_path_none_when_use_ssh_false(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_HOST": "localhost",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        cfg = load_config()
        assert cfg.use_ssh is False
        assert cfg.ssh_host is None
        assert cfg.ssh_key_path is None


class TestDirectConnectionMode:
    def test_no_ssh_fields_required_when_use_ssh_false(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "false",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        cfg = load_config()
        assert cfg.use_ssh is False
        assert cfg.db_host == "db.example.com"
        assert cfg.ssh_host is None
        assert cfg.ssh_key_path is None

    def test_use_ssh_false_from_env_various_falsy(self, monkeypatch):
        base = {
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "u",
            "BURROW_DB_PASSWORD": "p",
            "BURROW_DB_NAME": "d",
        }
        for falsy in ("false", "0", "no", "off", "False", "NO"):
            for k, v in base.items():
                monkeypatch.setenv(k, v)
            monkeypatch.setenv("BURROW_USE_SSH", falsy)
            cfg = load_config()
            assert cfg.use_ssh is False, f"expected False for BURROW_USE_SSH={falsy!r}"

    def test_use_ssh_true_still_requires_ssh_fields(self, monkeypatch):
        for k, v in {
            "BURROW_USE_SSH": "true",
            "BURROW_DB_HOST": "db.example.com",
            "BURROW_DB_USER": "appuser",
            "BURROW_DB_PASSWORD": "secret",
            "BURROW_DB_NAME": "appdb",
        }.items():
            monkeypatch.setenv(k, v)
        with pytest.raises(SystemExit):
            load_config()

    def test_use_ssh_false_from_config_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[default]\n"
            "use_ssh      = false\n"
            'db_host      = "localhost"\n'
            'db_port      = 5432\n'
            'db_user      = "appuser"\n'
            'db_name      = "appdb"\n'
        )
        monkeypatch.setenv("BURROW_CONFIG", str(config_file))
        monkeypatch.setenv("BURROW_DB_PASSWORD", "secret")
        cfg = load_config()
        assert cfg.use_ssh is False
        assert cfg.db_host == "localhost"
        assert cfg.ssh_host is None
