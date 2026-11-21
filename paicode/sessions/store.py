import json
import os
from pathlib import Path

from ..core.atomic import atomic_write_text, file_lock
from .models import SessionData, SessionRecord, new_session_id, now_iso
from .sanitize import sanitize_diffs, sanitize_messages, sanitize_transcript


def sessions_root() -> Path:
    override = os.getenv("PAICODE_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve() / "sessions"
    base = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base / "paicode" / "sessions"


class SessionStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else sessions_root()
        self.index_path = self.root / "index.json"

    def _ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass

    def _read_index(self) -> dict:
        if not self.index_path.exists():
            return {"version": 1, "sessions": []}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "sessions": []}
        if not isinstance(data, dict) or not isinstance(data.get("sessions"), list):
            return {"version": 1, "sessions": []}
        return data

    def _write_index(self, data: dict) -> None:
        self._ensure()
        atomic_write_text(self.index_path, json.dumps(data, indent=2), mode=0o600)

    def _session_path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.json"

    def create(self, workspace: str | Path, title: str = "") -> SessionData:
        self._ensure()
        index = self._read_index()
        existing = {record.get("id", "") for record in index["sessions"]}
        session_id = new_session_id(existing)
        stamp = now_iso()
        resolved = str(Path(workspace).expanduser().resolve())
        record = SessionRecord(
            id=session_id,
            workspace=resolved,
            created_at=stamp,
            last_opened_at=stamp,
            title=title or Path(resolved).name or resolved,
        )
        data = SessionData(record=record)
        self.save(data)
        return data

    def list(self) -> list[SessionRecord]:
        index = self._read_index()
        records = [SessionRecord.from_dict(item) for item in index["sessions"] if item.get("id")]
        return sorted(records, key=lambda record: record.last_opened_at, reverse=True)

    def find(self, query: str) -> SessionRecord | None:
        query = (query or "").strip()
        if not query:
            return None
        records = self.list()
        for record in records:
            if record.id == query:
                return record
        matches = [record for record in records if record.id.startswith(query)]
        return matches[0] if len(matches) == 1 else None

    def get(self, session_id: str) -> SessionData | None:
        record = self.find(session_id)
        if record is None:
            return None
        path = self._session_path(record.id)
        if not path.exists():
            return SessionData(record=record)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return SessionData(record=record)
        data.setdefault("id", record.id)
        data.setdefault("workspace", record.workspace)
        data.setdefault("created_at", record.created_at)
        data.setdefault("last_opened_at", record.last_opened_at)
        data.setdefault("title", record.title)
        return SessionData.from_dict(data)

    def save(self, data: SessionData) -> None:
        self._ensure()
        data.messages = sanitize_messages(data.messages)
        data.transcript = sanitize_transcript(data.transcript)
        data.diffs = sanitize_diffs(data.diffs)
        atomic_write_text(
            self._session_path(data.record.id),
            json.dumps(data.to_dict(), indent=2),
            mode=0o600,
        )
        with file_lock(self.index_path):
            index = self._read_index()
            sessions = [item for item in index["sessions"] if item.get("id") != data.record.id]
            sessions.append(data.record.to_dict())
            index["sessions"] = sessions
            self._write_index(index)

    def touch(self, session_id: str) -> SessionData | None:
        data = self.get(session_id)
        if data is None:
            return None
        data.record.last_opened_at = now_iso()
        self.save(data)
        return data
