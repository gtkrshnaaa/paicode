import json
import os
from datetime import datetime
from pathlib import Path

from ..db import Database
from .models import SessionData, SessionRecord, new_session_id, now_iso
from .sanitize import sanitize_diffs, sanitize_messages, sanitize_transcript


def legacy_sessions_root() -> Path:
    override = os.getenv("PAICODE_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve() / "sessions"
    base = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base / "paicode" / "sessions"


class SessionStore:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.initialize()
        self._migrate_legacy_json()

    def _migrate_legacy_json(self) -> None:
        legacy = legacy_sessions_root()
        index_path = legacy / "index.json"
        if not index_path.exists():
            return
        with self.db.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        if count:
            return
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        records = index.get("sessions", []) if isinstance(index, dict) else []
        for record in records:
            session_id = str(record.get("id", ""))
            if not session_id:
                continue
            session_file = legacy / f"{session_id}.json"
            if not session_file.exists():
                continue
            try:
                payload = json.loads(session_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payload.setdefault("id", session_id)
            payload.setdefault("workspace", record.get("workspace", ""))
            payload.setdefault("created_at", record.get("created_at", ""))
            payload.setdefault("last_opened_at", record.get("last_opened_at", ""))
            payload.setdefault("title", record.get("title", ""))
            data = SessionData.from_dict(payload)
            self._insert(data)
        target = legacy.with_name(
            f"{legacy.name}.migrated-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        try:
            legacy.rename(target)
        except OSError:
            pass

    def _insert(self, data: SessionData) -> None:
        data.messages = sanitize_messages(data.messages)
        data.transcript = sanitize_transcript(data.transcript)
        data.diffs = sanitize_diffs(data.diffs)
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions
                    (id, workspace, created_at, last_opened_at, title, stats_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data.record.id,
                    data.record.workspace,
                    data.record.created_at,
                    data.record.last_opened_at,
                    data.record.title,
                    json.dumps(data.stats),
                ),
            )
            self._replace_children(conn, data)

    def _replace_children(self, conn, data: SessionData) -> None:
        conn.execute("DELETE FROM session_messages WHERE session_id = ?", (data.record.id,))
        conn.execute("DELETE FROM session_transcript WHERE session_id = ?", (data.record.id,))
        conn.execute("DELETE FROM session_diffs WHERE session_id = ?", (data.record.id,))
        for index, message in enumerate(data.messages):
            conn.execute(
                """
                INSERT INTO session_messages
                    (session_id, seq, role, content_json, tool_calls_json, tool_call_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data.record.id,
                    index,
                    str(message.get("role", "")),
                    json.dumps(message.get("content")),
                    json.dumps(message.get("tool_calls")) if message.get("tool_calls") else None,
                    message.get("tool_call_id"),
                ),
            )
        for index, entry in enumerate(data.transcript):
            conn.execute(
                """
                INSERT INTO session_transcript
                    (session_id, seq, kind, text, name, status, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.record.id,
                    index,
                    str(entry.get("kind", "")),
                    entry.get("text"),
                    entry.get("name"),
                    entry.get("status"),
                    entry.get("detail"),
                ),
            )
        for index, diff in enumerate(data.diffs):
            conn.execute(
                """
                INSERT INTO session_diffs
                    (session_id, seq, path, diff, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data.record.id,
                    index,
                    str(diff.get("path", "")),
                    str(diff.get("diff", "")),
                    str(diff.get("created_at", "")),
                ),
            )

    def create(self, workspace: str | Path, title: str = "") -> SessionData:
        with self.db.connection() as conn:
            existing = {
                row["id"] for row in conn.execute("SELECT id FROM sessions").fetchall()
            }
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

    def _record(self, row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            workspace=row["workspace"],
            created_at=row["created_at"],
            last_opened_at=row["last_opened_at"],
            title=row["title"],
        )

    def list(self) -> list[SessionRecord]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY last_opened_at DESC"
            ).fetchall()
        return [self._record(row) for row in rows]

    def find(self, query: str) -> SessionRecord | None:
        query = (query or "").strip()
        if not query:
            return None
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (query,)).fetchone()
            if row:
                return self._record(row)
            rows = conn.execute(
                "SELECT * FROM sessions WHERE id LIKE ? ORDER BY last_opened_at DESC",
                (query + "%",),
            ).fetchall()
        return self._record(rows[0]) if len(rows) == 1 else None

    def get(self, session_id: str) -> SessionData | None:
        record = self.find(session_id)
        if record is None:
            return None
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (record.id,)).fetchone()
            if row is None:
                return None
            messages = []
            for item in conn.execute(
                "SELECT * FROM session_messages WHERE session_id = ? ORDER BY seq",
                (record.id,),
            ).fetchall():
                messages.append(
                    {
                        "role": item["role"],
                        "content": json.loads(item["content_json"]) if item["content_json"] else None,
                        "tool_calls": json.loads(item["tool_calls_json"])
                        if item["tool_calls_json"]
                        else None,
                        "tool_call_id": item["tool_call_id"],
                    }
                )
            transcript = []
            for item in conn.execute(
                "SELECT * FROM session_transcript WHERE session_id = ? ORDER BY seq",
                (record.id,),
            ).fetchall():
                entry = {"kind": item["kind"]}
                for key in ("text", "name", "status", "detail"):
                    if item[key] is not None:
                        entry[key] = item[key]
                transcript.append(entry)
            diffs = [
                {
                    "path": item["path"],
                    "diff": item["diff"],
                    "created_at": item["created_at"],
                }
                for item in conn.execute(
                    "SELECT * FROM session_diffs WHERE session_id = ? ORDER BY seq",
                    (record.id,),
                ).fetchall()
            ]
            stats = json.loads(row["stats_json"] or "{}")
        return SessionData(
            record=record,
            messages=messages,
            transcript=transcript,
            diffs=diffs,
            stats=stats,
        )

    def save(self, data: SessionData) -> None:
        data.messages = sanitize_messages(data.messages)
        data.transcript = sanitize_transcript(data.transcript)
        data.diffs = sanitize_diffs(data.diffs)
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (id, workspace, created_at, last_opened_at, title, stats_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    workspace = excluded.workspace,
                    last_opened_at = excluded.last_opened_at,
                    title = excluded.title,
                    stats_json = excluded.stats_json
                """,
                (
                    data.record.id,
                    data.record.workspace,
                    data.record.created_at,
                    data.record.last_opened_at,
                    data.record.title,
                    json.dumps(data.stats),
                ),
            )
            self._replace_children(conn, data)

    def touch(self, session_id: str) -> SessionData | None:
        data = self.get(session_id)
        if data is None:
            return None
        data.record.last_opened_at = now_iso()
        self.save(data)
        return data
