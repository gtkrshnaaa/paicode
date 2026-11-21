from pathlib import Path

from paicode.core.stats import UsageStats
from paicode.tools.registry import ToolRegistry


def make_registry(project: Path, stats: UsageStats | None = None) -> ToolRegistry:
    return ToolRegistry(project, stats or UsageStats(), [])


def write_file(registry: ToolRegistry, path: str, content: str) -> None:
    result = registry.execute("write", {"path": path, "content": content})
    assert result.ok, result.output


def run_command(
    registry: ToolRegistry,
    command: str,
    timeout: int = 120,
    cwd: str = "",
) -> str:
    result = registry.execute(
        "bash",
        {"command": command, "timeout": timeout, "cwd": cwd},
    )
    assert result.ok, result.output
    return result.output
