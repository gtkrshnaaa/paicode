from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    files_read: int = 0
    files_created: int = 0
    files_edited: int = 0
    commands: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def record_usage(self, prompt: int = 0, completion: int = 0, total: int = 0) -> None:
        self.prompt_tokens += max(0, int(prompt or 0))
        self.completion_tokens += max(0, int(completion or 0))
        self.total_tokens += max(0, int(total or 0))
        self.requests += 1

    def mark(self, kind: str, amount: int = 1) -> None:
        if kind == "read":
            self.files_read += amount
        elif kind == "created":
            self.files_created += amount
        elif kind == "edited":
            self.files_edited += amount
        elif kind == "command":
            self.commands += amount

    def reset(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.requests = 0
        self.files_read = 0
        self.files_created = 0
        self.files_edited = 0
        self.commands = 0
        self.started_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "requests": self.requests,
            "files_read": self.files_read,
            "files_created": self.files_created,
            "files_edited": self.files_edited,
            "commands": self.commands,
            "started_at": self.started_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UsageStats":
        stats = cls()
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "requests",
            "files_read",
            "files_created",
            "files_edited",
            "commands",
        ):
            try:
                setattr(stats, key, int(data.get(key, 0) or 0))
            except (TypeError, ValueError):
                setattr(stats, key, 0)
        started = data.get("started_at")
        if isinstance(started, str):
            try:
                stats.started_at = datetime.fromisoformat(started)
            except ValueError:
                pass
        return stats

    def summary(self) -> str:
        return (
            f"tokens {self.prompt_tokens}/{self.completion_tokens}/{self.total_tokens} "
            f"req {self.requests} "
            f"files r{self.files_read} c{self.files_created} e{self.files_edited} "
            f"cmds {self.commands}"
        )

    def detailed(self) -> str:
        elapsed = int((datetime.now() - self.started_at).total_seconds())
        return "\n".join(
            [
                f"Prompt tokens: {self.prompt_tokens}",
                f"Completion tokens: {self.completion_tokens}",
                f"Total tokens: {self.total_tokens}",
                f"Requests: {self.requests}",
                f"Files read: {self.files_read}",
                f"Files created: {self.files_created}",
                f"Files edited: {self.files_edited}",
                f"Commands run: {self.commands}",
                f"Elapsed: {elapsed}s",
            ]
        )
