from dataclasses import dataclass, field
from pathlib import Path


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
