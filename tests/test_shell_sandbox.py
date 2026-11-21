from pathlib import Path

import pytest

from paicode.tools.sandbox import sandbox_available
from paicode.tools.shell import ShellTools

pytestmark = pytest.mark.skipif(
    not sandbox_available(), reason="bubblewrap sandbox is not available"
)


def test_sandbox_allows_workspace_writes(project: Path, stats):
    tools = ShellTools(project, stats)
    assert tools.sandboxed
    result = tools.run("printf 'inside' > created.txt && mkdir -p nested")
    assert result.ok, result.output
    assert (project / "created.txt").read_text(encoding="utf-8") == "inside"
    assert (project / "nested").is_dir()


def test_sandbox_blocks_writes_outside_workspace(project: Path, stats):
    outside = Path("/var/tmp/paicode-sandbox-escape.txt")
    outside.unlink(missing_ok=True)
    tools = ShellTools(project, stats)
    result = tools.run(f"printf 'escaped' > {outside}")
    assert not result.ok
    assert not outside.exists()


def test_sandbox_hides_home_credentials(project: Path, stats):
    tools = ShellTools(project, stats)
    result = tools.run("test -e ~/.ssh || test -e ~/.config/paicode")
    assert not result.ok


def test_read_only_workspace_overlay_discards_writes(project: Path, stats):
    (project / "README.md").write_text("# Original\n", encoding="utf-8")
    tools = ShellTools(project, stats, read_only_workspace=True)
    result = tools.run("printf 'hacked\\n' > README.md && printf 'new\\n' > new.txt")
    assert result.ok, result.output
    assert (project / "README.md").read_text(encoding="utf-8") == "# Original\n"
    assert not (project / "new.txt").exists()


def test_sandbox_cache_is_writable(project: Path, stats, sandbox_cache: Path):
    tools = ShellTools(project, stats)
    result = tools.run("printf 'cached' > /tmp/paicode-cache/probe.txt")
    assert result.ok, result.output
    assert (sandbox_cache / "probe.txt").read_text(encoding="utf-8") == "cached"
