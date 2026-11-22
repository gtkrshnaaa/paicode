from pathlib import Path

from ..core.stats import UsageStats
from ..tools.shell import ShellTools

ARTIFACT_PREFIXES = (
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".venv/",
    "node_modules/",
    "build/",
    "dist/",
    "target/",
    "coverage/",
)
ARTIFACT_SUFFIXES = (".pyc", ".pyo", ".coverage")


def _parse_status(text: str) -> set[str]:
    paths: set[str] = set()
    for line in text.splitlines():
        if len(line) < 4:
            continue
        value = line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[-1]
        value = value.strip().strip('"')
        if not value or value.startswith(ARTIFACT_PREFIXES) or value.endswith(ARTIFACT_SUFFIXES):
            continue
        paths.add(value.replace("\\", "/"))
    return paths


def changed_files(root: Path, stats: UsageStats, stop_event=None) -> set[str]:
    shell = ShellTools(
        root,
        stats,
        timeout=30,
        stop_event=stop_event,
        read_only_workspace=True,
    )
    result = shell.run("git status --porcelain --untracked-files=all", timeout=30)
    if not result.ok:
        return set()
    body = result.output.split("--- OUTPUT ---", 1)[-1]
    return _parse_status(body)


def unowned_changes(
    changes: set[str],
    baseline: set[str],
    owned: set[str],
) -> list[str]:
    return sorted(changes - baseline - owned)
