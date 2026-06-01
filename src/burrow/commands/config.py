"""burrow config - manage profiles in the config file.

burrow config set                    interactive wizard for active profile
burrow --profile staging config set  wizard for a named profile
burrow config list                   list all profiles
burrow config get [key]              show resolved values (or one key)
burrow config unset <profile>        remove a profile
"""

import argparse
import getpass
import os
import sys
import tomllib
import tomli_w
from pathlib import Path

from burrow.config import (
    CONFIG_FILE_ENV,
    DEFAULT_CONFIG_PATH,
    DEFAULT_PROFILE,
    PROFILES_DIR,
    _FIELDS,
    _INT_FIELDS,
    _SENSITIVE,
    list_profiles,
    load_config,
)

_SSH_PROMPTS = [
    ("ssh_host", "Bastion host (IP or hostname)", True),
    ("ssh_user", "SSH username", False),
    ("ssh_key_path", "Path to SSH private key", True),
    ("ssh_port", "SSH port", False),
]

_DB_PROMPTS = [
    ("db_host", "Database host", True),
    ("db_port", "Database port", False),
    ("db_name", "Database name", True),
    ("db_user", "Database username", True),
]


def cmd_config(args: argparse.Namespace) -> None:
    sub = args.config_command
    if sub == "set":
        _cmd_set(args)
    elif sub == "list":
        _cmd_list()
    elif sub == "get":
        _cmd_get(args)
    elif sub == "unset":
        _cmd_unset(args)


def _cmd_set(args: argparse.Namespace) -> None:
    profile = args.profile
    config_path = _config_path()
    existing = _read_raw(config_path)
    current = existing.get(profile, {})

    print(f"Configuring profile: {profile}")
    print(f"Config file: {config_path}")
    print("Press Enter to keep the current value shown in [brackets].\n")

    updated: dict[str, object] = {}

    # db_type
    current_db_type = current.get("db_type", "postgres")
    raw = input(f"  Database type [postgres/mysql] [{current_db_type}]: ").strip().lower()
    db_type = raw if raw in ("postgres", "mysql") else current_db_type
    updated["db_type"] = db_type

    # use_ssh
    current_use_ssh = current.get("use_ssh", True)
    ssh_display = "[Y/n]" if current_use_ssh else "[y/N]"
    raw = input(f"  Use SSH tunnel? {ssh_display}: ").strip().lower()
    if not raw:
        use_ssh = current_use_ssh
    else:
        use_ssh = raw in ("y", "yes")
    updated["use_ssh"] = use_ssh

    # SSH prompts
    if use_ssh:
        for key, label, required in _SSH_PROMPTS:
            _, _, default = _FIELDS[key]
            current_val = current.get(key, default)
            display = f"[{current_val}]" if current_val is not None else ""
            value = input(f"  {label} {display}: ").strip()
            if not value and current_val is not None:
                updated[key] = current_val
            elif not value and required:
                print(f"  {key} is required.", file=sys.stderr)
                sys.exit(1)
            elif value:
                updated[key] = int(value) if key in _INT_FIELDS else value

    # DB prompts (db_port default depends on db_type)
    default_port = 3306 if db_type == "mysql" else 5432
    for key, label, required in _DB_PROMPTS:
        field_default = default_port if key == "db_port" else _FIELDS[key][2]
        current_val = current.get(key, field_default)
        display = f"[{current_val}]" if current_val is not None else ""
        value = input(f"  {label} {display}: ").strip()
        if not value and current_val is not None:
            updated[key] = current_val
        elif not value and required:
            print(f"  {key} is required.", file=sys.stderr)
            sys.exit(1)
        elif value:
            updated[key] = int(value) if key in _INT_FIELDS else value

    # db_schema — postgres only
    if db_type != "mysql":
        _, _, schema_default = _FIELDS["db_schema"]
        current_val = current.get("db_schema", schema_default)
        value = input(f"  Default schema [{current_val}]: ").strip()
        updated["db_schema"] = value or current_val

    # Password — written to separate file, never to config.toml
    password_file = _password_path(profile)
    has_existing = password_file.exists()
    display = "[********]" if has_existing else ""
    value = getpass.getpass(f"  Database password {display}: ").strip()
    if not value and has_existing:
        pass  # keep existing password file as-is
    elif not value:
        print("  db_password is required.", file=sys.stderr)
        sys.exit(1)
    else:
        _write_password(profile, value)

    existing[profile] = updated
    _write(config_path, existing)
    print(f"\nProfile '{profile}' saved to {config_path}")
    if value:
        print(f"Password saved to {password_file}")


def _cmd_list() -> None:
    config_path = _config_path()
    profiles = list_profiles()

    if not profiles:
        print("No profiles found. Run:\n  burrow config set")
        return

    print(f"Config file: {config_path}\n")
    print("Profiles:")
    active = os.environ.get("BURROW_PROFILE", DEFAULT_PROFILE)
    for p in profiles:
        marker = " *" if p == active else ""
        print(f"  {p}{marker}")


def _cmd_get(args: argparse.Namespace) -> None:
    config = load_config(args.profile)
    key = getattr(args, "key", None)

    if key:
        if not hasattr(config, key):
            print(f"error: unknown key '{key}'", file=sys.stderr)
            sys.exit(1)
        value = getattr(config, key)
        if key in _SENSITIVE:
            value = "********"
        print(value)
        return

    config_path = _config_path()
    print(f"Profile     : {args.profile}")
    print(
        f"Config file : {config_path}  {'(not found)' if not config_path.exists() else ''}\n"
    )

    print("Resolved config:")
    for key in _FIELDS:
        value = getattr(config, key, None)
        if value is None:
            continue
        env_var = _FIELDS[key][0]
        source = "  (from env)" if env_var in os.environ else ""
        print(f"  {key:<22} {value}{source}")

    # db_password is not in _FIELDS — show source separately
    if "BURROW_DB_PASSWORD" in os.environ:
        print(f"  {'db_password':<22} ********  (from env)")
    elif _password_path(args.profile).exists():
        print(f"  {'db_password':<22} ********  (from password file)")


def _cmd_unset(args: argparse.Namespace) -> None:
    profile = args.profile_name
    config_path = _config_path()
    data = _read_raw(config_path)

    if profile not in data:
        print(f"error: profile '{profile}' not found in {config_path}", file=sys.stderr)
        sys.exit(1)

    confirm = (
        input(f"Remove profile '{profile}' from {config_path}? [y/N] ").strip().lower()
    )
    if confirm != "y":
        print("Aborted.")
        return

    del data[profile]
    _write(config_path, data)

    pw_file = _password_path(profile)
    if pw_file.exists():
        pw_file.unlink()
        print(f"Password file removed: {pw_file}")

    print(f"Profile '{profile}' removed.")


def _config_path() -> Path:
    return Path(os.environ.get(CONFIG_FILE_ENV, DEFAULT_CONFIG_PATH))


def _password_path(profile: str) -> Path:
    return PROFILES_DIR / f"{profile}.password"


def _write_password(profile: str, password: str) -> None:
    path = _password_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(password, encoding="utf-8")
    path.chmod(0o600)


def _read_raw(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as fh:
        return tomllib.load(fh)


def _write(config_path: Path, data: dict[str, object]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "wb") as fh:
        tomli_w.dump(data, fh)
