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
