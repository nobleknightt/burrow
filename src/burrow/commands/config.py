"""burrow config - manage profiles in the config file.

burrow config set                    interactive wizard for active profile
burrow config set --profile staging  wizard for a named profile
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
    _FIELDS,
    _SENSITIVE,
    list_profiles,
    load_config,
)

# (key, label, required, is_secret)
_PROMPTS = [
    # SSH
    ("ssh_host", "Bastion host (IP or hostname)", True, False),
    ("ssh_user", "SSH username", False, False),
    ("ssh_key_path", "Path to SSH private key", True, False),
    ("ssh_port", "SSH port", False, False),
    # RDS
    ("db_host", "Database host", True, False),
    ("db_port", "Database port", False, False),
    # Credentials
    ("db_name", "Database name", True, False),
    ("db_user", "Database username", True, False),
    ("db_password", "Database password", True, True),
    ("db_schema", "Default schema", False, False),
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

    for key, label, required, is_secret in _PROMPTS:
        _, _, default = _FIELDS[key]
        current_val = current.get(key, default)

        if is_secret:
            display = "[********]" if current_val else ""
            prompt_str = f"  {label} {display}: "
            value = getpass.getpass(prompt_str).strip()
            if not value and current_val:
                updated[key] = current_val  # keep existing
            elif not value and required:
                print(f"  {key} is required.", file=sys.stderr)
                sys.exit(1)
            elif value:
                updated[key] = value
        else:
            display = f"[{current_val}]" if current_val is not None else ""
            prompt_str = f"  {label} {display}: "
            value = input(prompt_str).strip()
            if not value and current_val is not None:
                updated[key] = current_val
            elif not value and required:
                print(f"  {key} is required.", file=sys.stderr)
                sys.exit(1)
            elif value:
                # coerce int fields
                from burrow.config import _INT_FIELDS

                updated[key] = int(value) if key in _INT_FIELDS else value

    existing[profile] = updated
    _write(config_path, existing)
    print(f"\nProfile '{profile}' saved to {config_path}")


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
        if key in _SENSITIVE:
            value = "********"
        env_var = _FIELDS[key][0]
        source = "  (from env)" if env_var in os.environ else ""
        print(f"  {key:<22} {value}{source}")


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
    print(f"Profile '{profile}' removed.")


def _config_path() -> Path:
    return Path(os.environ.get(CONFIG_FILE_ENV, DEFAULT_CONFIG_PATH))


def _read_raw(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as fh:
        return tomllib.load(fh)


def _write(config_path: Path, data: dict[str, object]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "wb") as fh:
        tomli_w.dump(data, fh)
