"""
Configuration resolution - mirrors the aws/gh cli pattern:

Priority (highest to lowest):
  1. Environment variables  BURROW_SSH_HOST, BURROW_DB_PASSWORD, etc.
  2. Profile in config file  ~/.config/burrow/config.toml  (or $BURROW_CONFIG)
  3. [default] profile as fallback

Config file format:
  [default]
  ssh_host     = "bastion.example.com"
  ssh_user     = "ec2-user"
  ssh_key_path = "~/.ssh/id_rsa"
  db_host     = "mydb.cluster-xyz.us-east-1.rds.amazonaws.com"
  db_user      = "myuser"
  db_password  = "secret"
  db_name      = "mydb"
  db_schema    = "public"

  [staging]
  ssh_host     = "bastion-staging.example.com"
  # ...
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

# Maps config key to (env var, required, default)
_FIELDS: dict[str, tuple[str, bool, object]] = {
    "ssh_host": ("BURROW_SSH_HOST", True, None),
    "ssh_user": ("BURROW_SSH_USER", False, "ec2-user"),
    "ssh_key_path": ("BURROW_SSH_KEY_PATH", True, None),
    "ssh_port": ("BURROW_SSH_PORT", False, 22),
    "db_host": ("BURROW_DB_HOST", True, None),
    "db_port": ("BURROW_DB_PORT", False, 5432),
    "db_user": ("BURROW_DB_USER", True, None),
    "db_password": ("BURROW_DB_PASSWORD", True, None),
    "db_name": ("BURROW_DB_NAME", True, None),
    "db_schema": ("BURROW_DB_SCHEMA", False, "public"),
    "tunnel_local_port": ("BURROW_TUNNEL_LOCAL_PORT", False, 0),
    "connection_timeout": ("BURROW_CONNECTION_TIMEOUT", False, 10),
}

_INT_FIELDS = {"ssh_port", "db_port", "tunnel_local_port", "connection_timeout"}
_SENSITIVE = {"db_password"}

CONFIG_FILE_ENV = "BURROW_CONFIG"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "burrow" / "config.toml"
DEFAULT_PROFILE = "default"


@dataclass
class DatabaseConfig:
    ssh_host: str
    ssh_key_path: str
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    ssh_user: str = "ec2-user"
    ssh_port: int = 22
    db_port: int = 5432
    db_schema: str = "public"
    tunnel_local_port: int = 0
    connection_timeout: int = 10

    def __post_init__(self) -> None:
        # Expand ~ in key path
        self.ssh_key_path = str(Path(self.ssh_key_path).expanduser())


def load_config(profile: str = DEFAULT_PROFILE) -> DatabaseConfig:
    """
    Resolve configuration for the given profile.
    Env vars always win; config file fills in the rest.
    """
    file_values = _read_config_file(profile)
    resolved: dict[str, object] = {}
    missing: list[str] = []

    for key, (env_var, required, default) in _FIELDS.items():
        # 1. env var
        if env_var in os.environ:
            value = os.environ[env_var]
            resolved[key] = int(value) if key in _INT_FIELDS else value
            continue

        # 2. config file
        if key in file_values:
            value = file_values[key]
            resolved[key] = int(value) if key in _INT_FIELDS else value
            continue

        # 3. default
        if default is not None:
            resolved[key] = default
            continue

        if required:
            missing.append(f"  {key}  (env: {env_var})")

    if missing:
        hint = _missing_hint(profile, missing)
        raise SystemExit(hint)

    return DatabaseConfig(**resolved)


def _read_config_file(profile: str) -> dict[str, object]:
    config_path = Path(os.environ.get(CONFIG_FILE_ENV, DEFAULT_CONFIG_PATH))

    if not config_path.exists():
        return {}

    with open(config_path, "rb") as fh:
        data = tomllib.load(fh)

    if profile not in data:
        if profile != DEFAULT_PROFILE:
            raise SystemExit(
                f"error: profile '{profile}' not found in {config_path}\n"
                f"available profiles: {', '.join(data.keys())}"
            )
        return {}

    return data[profile]


def _missing_hint(profile: str, missing: list[str]) -> str:
    config_path = Path(os.environ.get(CONFIG_FILE_ENV, DEFAULT_CONFIG_PATH))
    lines = [
        f"error: missing required config for profile '{profile}':",
        *missing,
        "",
        "set them via environment variables, or add a config file:",
        f"  {config_path}",
        "",
        "example config:",
        "  [default]",
        '  ssh_host     = "bastion.example.com"',
        '  ssh_key_path = "~/.ssh/id_rsa"',
        '  db_host     = "mydb.cluster.us-east-1.rds.amazonaws.com"',
        '  db_user      = "myuser"',
        '  db_password  = "secret"',
        '  db_name      = "mydb"',
    ]
    return "\n".join(lines)


def list_profiles() -> list[str]:
    """Return profile names from the config file, or [] if none exists."""
    config_path = Path(os.environ.get(CONFIG_FILE_ENV, DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return []
    with open(config_path, "rb") as fh:
        data = tomllib.load(fh)
    return list(data.keys())
