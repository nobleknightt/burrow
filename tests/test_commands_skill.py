"""Tests for burrow skill install."""

from types import SimpleNamespace

import pytest

from burrow.commands.skill import Agent, _cmd_install, _parse_version


def make_args(path=None, agent=None):
    return SimpleNamespace(path=path, agent=agent)


class TestInstallToPath:
    def test_installs_skill_md(self, tmp_path):
        dest_dir = tmp_path / "skills"
        _cmd_install(make_args(path=str(dest_dir)))
        assert (dest_dir / "SKILL.md").exists()

    def test_skill_md_contains_name(self, tmp_path):
        dest_dir = tmp_path / "skills"
        _cmd_install(make_args(path=str(dest_dir)))
        content = (dest_dir / "SKILL.md").read_text()
        assert "burrow" in content

    def test_creates_parent_dirs(self, tmp_path):
        dest_dir = tmp_path / "a" / "b" / "c"
        _cmd_install(make_args(path=str(dest_dir)))
        assert (dest_dir / "SKILL.md").exists()


class TestInstallToAgent:
    def test_invalid_agent_exits(self):
        with pytest.raises(SystemExit):
            _cmd_install(make_args(agent="nonexistent-agent"))

    def test_valid_agent_installs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        dest = tmp_path / ".claude" / "skills" / "burrow" / "SKILL.md"
        _cmd_install(make_args(agent="claude-code"))
        assert dest.exists()

    def test_multiple_agents_install(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        _cmd_install(make_args(agent="claude-code,cursor"))
        assert (tmp_path / ".claude" / "skills" / "burrow" / "SKILL.md").exists()
        assert (tmp_path / ".cursor" / "skills" / "burrow" / "SKILL.md").exists()

    def test_codex_installs_to_agents_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        _cmd_install(make_args(agent="codex"))
        assert (tmp_path / ".agents" / "skills" / "burrow" / "SKILL.md").exists()


class TestParseVersion:
    def test_parses_version(self):
        content = '---\nname: test\nversion: "1.2.3"\n---\n# body'
        assert _parse_version(content) == '"1.2.3"'

    def test_no_frontmatter(self):
        assert _parse_version("# just markdown") is None

    def test_missing_version(self):
        content = "---\nname: test\n---\n# body"
        assert _parse_version(content) is None
