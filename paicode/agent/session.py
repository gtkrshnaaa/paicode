from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..core.atomic import atomic_write_text
from ..core.paths import history_dir, state_dir


@dataclass
class SessionState:
    root: Path
    messages: list[dict] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    last_request: str = ""
    turns: int = 0
    last_summary: str = ""

    def add_changed(self, paths: list[str]) -> None:
        for path in paths:
            if path and path not in self.changed_files:
                self.changed_files.append(path)


def read_brain(root: Path) -> str:
    path = state_dir(root) / "session.md"
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_brain(state: SessionState, stats=None) -> None:
    path = state_dir(state.root) / "session.md"
    lines = [
        "# Paicode Session",
        "",
        f"Updated: {datetime.now().isoformat(timespec='seconds')}",
        f"Turns: {state.turns}",
        f"Last request: {state.last_request.strip()[:500]}",
        f"Last summary: {state.last_summary.strip()[:800]}",
        "",
        "Files changed:",
    ]
    if state.changed_files:
        lines.extend(f"- {item}" for item in state.changed_files[-50:])
    else:
        lines.append("- none")
    if stats is not None:
        lines.extend(["", f"Tokens: {stats.prompt_tokens}/{stats.completion_tokens}/{stats.total_tokens}"])
    atomic_write_text(path, "\n".join(lines), mode=0o644)


def append_history(root: Path, title: str, body: str) -> Path:
    directory = history_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"session-{datetime.now().strftime('%Y%m%d')}.log"
    stamp = datetime.now().isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"\n=== {stamp} | {title} ===\n{body.strip()}\n")
    return path
