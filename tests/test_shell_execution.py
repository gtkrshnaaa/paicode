import threading
import time
from pathlib import Path

import pytest

from paicode.core.errors import PathSecurityError
from paicode.tools.shell import ShellTools


def test_pipeline_redirection_and_multi_command(project: Path, stats):
    tools = ShellTools(project, stats)
    result = tools.run(
        "mkdir -p src && printf 'alpha\\nbeta\\n' > src/data.txt && "
        "grep beta src/data.txt | tr a-z A-Z > src/out.txt"
    )
    assert result.ok, result.output
    assert (project / "src/out.txt").read_text(encoding="utf-8").strip() == "BETA"


def test_exit_code_and_stderr(project: Path, stats):
    tools = ShellTools(project, stats)
    result = tools.run("printf 'boom\\n' >&2; exit 7")
    assert not result.ok
    assert "exit 7" in result.output
    assert "boom" in result.output


def test_working_directory(project: Path, stats):
    (project / "sub").mkdir()
    tools = ShellTools(project, stats)
    result = tools.run("pwd", cwd="sub")
    assert result.ok
    assert result.output.rstrip().endswith("/sub")


def test_working_directory_cannot_escape(project: Path, stats):
    tools = ShellTools(project, stats)
    with pytest.raises(PathSecurityError):
        tools.run("pwd", cwd="..")


def test_timeout_kills_process_group(project: Path, stats):
    tools = ShellTools(project, stats)
    started = time.monotonic()
    result = tools.run("sleep 5 & wait", timeout=1)
    elapsed = time.monotonic() - started
    assert not result.ok
    assert "timeout after 1s" in result.output
    assert elapsed < 4


def test_timeout_kills_child_processes(project: Path, stats):
    tools = ShellTools(project, stats)
    result = tools.run("(sleep 2; touch late.txt) & wait", timeout=1)
    assert not result.ok
    time.sleep(2.5)
    assert not (project / "late.txt").exists()


def test_stop_event_kills_command(project: Path, stats):
    stop = threading.Event()
    tools = ShellTools(project, stats, stop_event=stop)
    threading.Timer(0.3, stop.set).start()
    started = time.monotonic()
    result = tools.run("sleep 5", timeout=10)
    elapsed = time.monotonic() - started
    assert not result.ok
    assert "stopped by user" in result.output
    assert elapsed < 4


def test_output_is_bounded(project: Path, stats):
    tools = ShellTools(project, stats)
    result = tools.run("python3 -c \"print('x' * 250000)\"", timeout=30)
    assert result.ok
    assert "output truncated" in result.output
    assert len(result.output) <= 210_000


def test_secret_environment_is_scrubbed(project: Path, stats, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("MY_TOKEN", "token-value")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")
    monkeypatch.setenv("VISIBLE_FLAG", "visible")
    tools = ShellTools(project, stats)
    result = tools.run("env")
    assert result.ok
    assert "OPENAI_API_KEY" not in result.output
    assert "MY_TOKEN" not in result.output
    assert "SSH_AUTH_SOCK" not in result.output
    assert "VISIBLE_FLAG=visible" in result.output


def test_git_workflow(project: Path, stats):
    tools = ShellTools(project, stats)
    assert tools.run("git init -q").ok
    assert tools.run("git config user.name Test").ok
    assert tools.run("git config user.email test@example.com").ok
    assert tools.run("git add README.md").ok
    assert tools.run("git commit -q -m initial").ok
    result = tools.run("git log --oneline")
    assert result.ok
    assert "initial" in result.output


def test_npm_test_script(project: Path, stats):
    (project / "package.json").write_text(
        '{"name":"matrix","version":"1.0.0","scripts":{"test":"node --test"}}',
        encoding="utf-8",
    )
    (project / "math.test.js").write_text(
        "import test from 'node:test';\n"
        "import assert from 'node:assert/strict';\n"
        "test('adds', () => assert.equal(1 + 1, 2));\n",
        encoding="utf-8",
    )
    tools = ShellTools(project, stats)
    result = tools.run("npm test", timeout=120)
    assert result.ok, result.output
    assert "pass" in result.output.lower()


def test_make_c_build(project: Path, stats):
    (project / "main.c").write_text(
        "#include <stdio.h>\nint main(void){puts(\"c-ok\");return 0;}\n",
        encoding="utf-8",
    )
    (project / "Makefile").write_text(
        "test: main\n\t./main | grep -q c-ok\n\nmain: main.c\n\t$(CC) -std=c11 -Wall -Werror main.c -o main\n",
        encoding="utf-8",
    )
    tools = ShellTools(project, stats)
    result = tools.run("make test", timeout=120)
    assert result.ok, result.output


def test_dangerous_commands_are_rejected(project: Path, stats):
    tools = ShellTools(project, stats)
    for command in [
        "sudo ls",
        "mkfs.ext4 /dev/sda",
        "shutdown now",
        "rm -rf /",
        "rm -rf ~",
        "chmod -R 777 /",
        "docker run --privileged image",
    ]:
        with pytest.raises(ValueError):
            tools.run(command)


def test_direct_mode_runs_without_sandbox(project: Path, stats, monkeypatch):
    monkeypatch.setenv("PAICODE_SHELL_SANDBOX", "direct")
    tools = ShellTools(project, stats)
    assert not tools.sandboxed
    result = tools.run("printf 'direct' > out.txt")
    assert result.ok
    assert (project / "out.txt").read_text(encoding="utf-8") == "direct"
