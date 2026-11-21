import secrets
from dataclasses import dataclass, field
from datetime import datetime


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def display_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    return parsed.strftime("%Y-%m-%d %H:%M:%S %z")


def new_session_id(existing: set[str]) -> str:
    while True:
        candidate = f"s-{secrets.token_hex(4)}"
        if candidate not in existing:
            return candidate


@dataclass
class SessionRecord:
    id: str
    workspace: str
    created_at: str
    last_opened_at: str
    title: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace": self.workspace,
            "created_at": self.created_at,
            "last_opened_at": self.last_opened_at,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionRecord":
        return cls(
            id=str(data.get("id", "")),
            workspace=str(data.get("workspace", "")),
            created_at=str(data.get("created_at", "")),
            last_opened_at=str(data.get("last_opened_at", "")),
            title=str(data.get("title", "")),
        )


@dataclass
class SessionData:
    record: SessionRecord
    messages: list[dict] = field(default_factory=list)
    transcript: list[dict] = field(default_factory=list)
    diffs: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            **self.record.to_dict(),
            "messages": self.messages,
            "transcript": self.transcript,
            "diffs": self.diffs,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        return cls(
            record=SessionRecord.from_dict(data),
            messages=list(data.get("messages", [])),
            transcript=list(data.get("transcript", [])),
            diffs=list(data.get("diffs", [])),
            stats=dict(data.get("stats", {})),
        )
