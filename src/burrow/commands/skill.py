"""burrow skill - manage Claude Code skill installation."""

import argparse
import importlib.resources
import sys
from pathlib import Path


def _bundled_skill() -> str:
    return (
        importlib.resources.files("burrow")
        .joinpath("SKILL.md")
        .read_text(encoding="utf-8")
    )


def _parse_version(content: str) -> str | None:
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip()
    return None


def cmd_skill(args: argparse.Namespace) -> None:
    if args.skill_command == "install":
        _cmd_install(args)


def _cmd_install(args: argparse.Namespace) -> None:
    content = _bundled_skill()
    if getattr(args, "path", None):
        dest_dir = Path(args.path)
    else:
        dest_dir = Path.home() / ".claude" / "skills" / "burrow"
    dest = dest_dir / "SKILL.md"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    dest.chmod(0o644)
    print(f"Installed to {dest}")


def check_skill_outdated() -> None:
    """Warn if the installed skill version differs from the bundled one."""
    try:
        installed = Path.home() / ".claude" / "skills" / "burrow" / "SKILL.md"
        if not installed.exists():
            return
        bundled_ver = _parse_version(_bundled_skill())
        installed_ver = _parse_version(installed.read_text(encoding="utf-8"))
        if bundled_ver and installed_ver and bundled_ver != installed_ver:
            print(
                "warning: burrow skill is outdated, run 'burrow skill install' to update",
                file=sys.stderr,
            )
    except Exception:
        pass
