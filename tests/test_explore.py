from pathlib import Path

import pytest

from paicode.core.errors import PathSecurityError
from paicode.core.stats import UsageStats
from paicode.tools.explore import ExploreTools
from paicode.tools.fs import FileTools

REASON = "Need host configuration context for the current task"


def test_explore_reads_file_outside_workspace(project: Path, tmp_path: Path):
    outside = tmp_path / "host-info.txt"
    outside.write_text("os-release-like content", encoding="utf-8")
    tools = ExploreTools(project, UsageStats())
    result = tools.explore(str(outside), REASON)
    assert result.ok
    assert "Scope: system" in result.output
    assert f"Reason: {REASON}" in result.output
    assert "os-release-like content" in result.output
    assert f"Writes remain confined to: {project}" in result.output


def test_explore_workspace_scope(project: Path):
    (project / "local.txt").write_text("local", encoding="utf-8")
    result = ExploreTools(project, UsageStats()).explore("local.txt", REASON)
    assert "Scope: workspace" in result.output
    assert "local" in result.output


def test_explore_lists_directory_and_hides_restricted_entries(project: Path, tmp_path: Path):
    directory = tmp_path / "outside-dir"
    directory.mkdir()
    (directory / "app.conf").write_text("safe", encoding="utf-8")
    (directory / ".env").write_text("SECRET=1", encoding="utf-8")
    ssh_dir = directory / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_rsa").write_text("private", encoding="utf-8")

    tools = ExploreTools(project, UsageStats())
    result = tools.explore(str(directory), REASON, pattern="*.conf")
    assert "app.conf" in result.output
    assert ".env" not in result.output
    assert ".ssh" not in result.output
    assert "restricted entries hidden" in result.output


def test_explore_requires_a_concrete_reason(project: Path, tmp_path: Path):
    outside = tmp_path / "host-info.txt"
    outside.write_text("content", encoding="utf-8")
    tools = ExploreTools(project, UsageStats())
    with pytest.raises(ValueError, match="concrete reason"):
        tools.explore(str(outside), "short")


def test_explore_blocks_ssh_keys(project: Path, tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True)
    key = ssh_dir / "id_rsa"
    key.write_text("private", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: home)

    with pytest.raises(PathSecurityError, match="restricted"):
        ExploreTools(project, UsageStats()).explore(str(key), REASON)


def test_explore_blocks_pseudo_filesystems(project: Path):
    with pytest.raises(PathSecurityError, match="restricted"):
        ExploreTools(project, UsageStats()).explore("/proc/self/environ", REASON)


def test_explore_blocks_password_files_and_private_suffixes(project: Path, tmp_path: Path):
    tools = ExploreTools(project, UsageStats())
    with pytest.raises(PathSecurityError, match="restricted"):
        tools.explore("/etc/shadow", REASON)

    private = tmp_path / "server.pem"
    private.write_text("private", encoding="utf-8")
    with pytest.raises(PathSecurityError, match="restricted"):
        tools.explore(str(private), REASON)


def test_writes_outside_workspace_remain_blocked(project: Path):
    tools = FileTools(project, UsageStats())
    with pytest.raises(PathSecurityError):
        tools.write("../escaped.txt", "nope")
