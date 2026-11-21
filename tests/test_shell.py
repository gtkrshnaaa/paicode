from pathlib import Path

import pytest

from paicode.tools.shell import ShellTools


def test_allowed_command_runs(project: Path, stats):
    tools = ShellTools(project, stats)
    result = tools.run("ls")
    assert result.ok
    assert "README.md" in result.output
    assert stats.commands == 1


def test_rejects_unknown_binary(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="allowlist"):
        tools.run("rm -rf .")


def test_rejects_absolute_path_arguments(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="escapes"):
        tools.run("cat /etc/passwd")


def test_rejects_git_push(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="git push"):
        tools.run("git push")


def test_rejects_inline_python(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="Inline Python"):
        tools.run("python3 -c 'print(1)'")


def test_rejects_shell_operators(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="Shell operators"):
        tools.run("ls; whoami")


def test_read_only_system_commands(project: Path, stats):
    tools = ShellTools(project, stats)
    assert tools.run("uname -a").ok
    assert tools.run("df -h").ok


def test_rejects_destructive_systemctl(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="systemctl restart"):
        tools.run("systemctl restart nginx")


def test_rejects_destructive_journalctl(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(ValueError, match="Destructive journalctl"):
        tools.run("journalctl --vacuum-size=10M")
