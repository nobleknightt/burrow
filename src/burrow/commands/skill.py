"""burrow skill - manage Agent Skills installation."""

import argparse
import importlib.resources
import sys
from enum import Enum
from pathlib import Path


class Agent(str, Enum):
    AGENTS   = "agents"       # universal ~/.agents/skills/
    CLAUDE   = "claude-code"
    CODEX    = "codex"        # uses ~/.agents/skills/ natively
    COPILOT  = "copilot"
    CURSOR   = "cursor"
    OPENCODE = "opencode"

    def __str__(self) -> str:
        return self.value

    @property
    def skill_dir(self) -> Path:
        home = Path.home()
        return {
            Agent.AGENTS:   home / ".agents"              / "skills" / "burrow",
            Agent.CLAUDE:   home / ".claude"              / "skills" / "burrow",
            Agent.CODEX:    home / ".agents"              / "skills" / "burrow",
            Agent.COPILOT:  home / ".copilot"             / "skills" / "burrow",
            Agent.CURSOR:   home / ".cursor"              / "skills" / "burrow",
            Agent.OPENCODE: home / ".config" / "opencode" / "skills" / "burrow",
        }[self]


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


def _install_to(dest_dir: Path, content: str) -> None:
    dest = dest_dir / "SKILL.md"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    dest.chmod(0o644)
    print(f"Installed to {dest}")


def cmd_skill(args: argparse.Namespace) -> None:
    if args.skill_command == "install":
        _cmd_install(args)


def _cmd_install(args: argparse.Namespace) -> None:
    content = _bundled_skill()

    if getattr(args, "path", None):
        _install_to(Path(args.path), content)
        return

    agent_arg = getattr(args, "agent", None)
    if agent_arg:
        names = [a.strip() for a in agent_arg.split(",")]
        try:
            agents = [Agent(name) for name in names]
        except ValueError as exc:
            valid = ", ".join(a.value for a in Agent)
            print(f"error: {exc}", file=sys.stderr)
            print(f"valid agents: {valid}", file=sys.stderr)
            sys.exit(1)
        for agent in agents:
            _install_to(agent.skill_dir, content)
        return

    _install_to(Agent.AGENTS.skill_dir, content)


def check_skill_outdated() -> None:
    """Warn if any installed skill copy is older than the bundled version."""
    try:
        bundled_ver = _parse_version(_bundled_skill())
        if not bundled_ver:
            return
        for agent in Agent:
            path = agent.skill_dir / "SKILL.md"
            if not path.exists():
                continue
            installed_ver = _parse_version(path.read_text(encoding="utf-8"))
            if installed_ver and bundled_ver != installed_ver:
                print(
                    "warning: burrow skill is outdated, run 'burrow skill install' to update",
                    file=sys.stderr,
                )
                return
    except Exception:
        pass
