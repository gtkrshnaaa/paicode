import json
import threading
from datetime import datetime
from pathlib import Path

from .settings import Settings, load_settings, state_dir


class Telemetry:
    def __init__(self, root: Path, settings: Settings | None = None):
        self.root = Path(root)
        self.settings = settings or load_settings(root)
        self.enabled = self.settings.telemetry
        self.path = state_dir() / "telemetry" / "events.jsonl"
        self._lock = threading.Lock()

    def emit(self, kind: str, **payload) -> None:
        if not self.enabled:
            return
        record = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "kind": kind,
            "workspace": str(self.root),
            **payload,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            return
