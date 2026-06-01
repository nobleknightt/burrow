"""
Configuration resolution - mirrors the aws/gh cli pattern:

Priority (highest to lowest):
  1. Environment variables  BURROW_SSH_HOST, BURROW_DB_PASSWORD, etc.
  2. Profile in config file  ~/.config/burrow/config.toml  (or $BURROW_CONFIG)
  3. [default] profile as fallback

Passwords are never stored in config.toml. Set BURROW_DB_PASSWORD or run
`burrow config set` to store the password in ~/.config/burrow/profiles/<profile>.password.

Config file format (SSH tunnel mode):
  [default]
  db_type      = "postgres"
  use_ssh      = true
  ssh_host     = "bastion.example.com"
  ssh_user     = "ec2-user"
  ssh_key_path = "~/.ssh/id_rsa"
  db_host      = "db.cluster-xyz.us-east-1.rds.amazonaws.com"
  db_user      = "appuser"
  db_name      = "appdb"
  db_schema    = "public"

Config file format (direct connection mode):
  [local]
  db_type      = "mysql"
  use_ssh      = false
  db_host      = "localhost"
  db_user      = "appuser"
  db_name      = "appdb"
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

# Maps config key to (env var, required, default)
_FIELDS: dict[str, tuple[str, bool, object]] = {
    "db_type": ("BURROW_DB_TYPE", False, "postgres"),
    "use_ssh": ("BURROW_USE_SSH", False, True),
    "ssh_host": ("BURROW_SSH_HOST", False, None),  # conditionally required when use_ssh=True
    "ssh_user": ("BURROW_SSH_USER", False, "ec2-user"),
    "ssh_key_path": ("BURROW_SSH_KEY_PATH", False, None),  # conditionally required when use_ssh=True
    "ssh_port": ("BURROW_SSH_PORT", False, 22),
    "db_host": ("BURROW_DB_HOST", True, None),
    "db_port": ("BURROW_DB_PORT", False, None),  # default depends on db_type: postgres=5432, mysql=3306
    "db_user": ("BURROW_DB_USER", True, None),
    "db_name": ("BURROW_DB_NAME", True, None),
    "db_schema": ("BURROW_DB_SCHEMA", False, "public"),
    "tunnel_local_port": ("BURROW_TUNNEL_LOCAL_PORT", False, 0),
    "connection_timeout": ("BURROW_CONNECTION_TIMEOUT", False, 10),
}

_INT_FIELDS = {"ssh_port", "db_port", "tunnel_local_port", "connection_timeout"}
_BOOL_FIELDS = {"use_ssh"}
_SENSITIVE = {"db_password"}

CONFIG_FILE_ENV = "BURROW_CONFIG"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "burrow" / "config.toml"
PROFILES_DIR = Path.home() / ".config" / "burrow" / "profiles"
DEFAULT_PROFILE = "default"


@dataclass
class DatabaseConfig:
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    db_type: str = "postgres"
    use_ssh: bool = True
    ssh_host: str | None = None
    ssh_key_path: str | None = None
    ssh_user: str = "ec2-user"
    ssh_port: int = 22
    db_port: int = 5432
    db_schema: str = "public"
    tunnel_local_port: int = 0
    connection_timeout: int = 10

    def __post_init__(self) -> None:
        if self.ssh_key_path:
            self.ssh_key_path = str(Path(self.ssh_key_path).expanduser())


def _read_password_file(profile: str) -> str | None:
    path = PROFILES_DIR / f"{profile}.password"
    if path.exists():
        return path.read_text(encoding="utf-8").strip() or None
    return None


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
            if key in _INT_FIELDS:
                resolved[key] = int(value)
            elif key in _BOOL_FIELDS:
                resolved[key] = value.lower() not in ("false", "0", "no", "off")
            else:
                resolved[key] = value
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

    # Apply type-aware port default when not explicitly set
    if "db_port" not in resolved:
        resolved["db_port"] = 3306 if resolved.get("db_type") == "mysql" else 5432

    # db_password: env var first, then password file — never from config.toml
    db_password = os.environ.get("BURROW_DB_PASSWORD") or _read_password_file(profile)
    if not db_password:
        missing.append(
            "  db_password  (env: BURROW_DB_PASSWORD or run 'burrow config set')"
        )
    else:
        resolved["db_password"] = db_password

    # SSH fields are conditionally required when use_ssh is True
    if resolved.get("use_ssh", True):
        if not resolved.get("ssh_host"):
            missing.append("  ssh_host  (env: BURROW_SSH_HOST)")
        if not resolved.get("ssh_key_path"):
            missing.append("  ssh_key_path  (env: BURROW_SSH_KEY_PATH)")

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
    lines = [
        f"error: missing required config for profile '{profile}':",
        *missing,
        "",
        "run the setup wizard to configure this profile:",
        "  burrow config set",
        "",
        "passwords are stored in:",
        f"  {PROFILES_DIR}/<profile>.password",
        "or set BURROW_DB_PASSWORD in your environment.",
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
