import threading
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    requests: int = 0
    files_read: int = 0
    files_created: int = 0
    files_edited: int = 0
    commands: int = 0
    cost_usd: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def record_usage(
        self,
        prompt: int = 0,
        completion: int = 0,
        total: int = 0,
        cache_hit: int = 0,
        cache_miss: int = 0,
    ) -> None:
        with self._lock:
            self.prompt_tokens += max(0, int(prompt or 0))
            self.completion_tokens += max(0, int(completion or 0))
            self.total_tokens += max(0, int(total or 0))
            self.cache_hit_tokens += max(0, int(cache_hit or 0))
            self.cache_miss_tokens += max(0, int(cache_miss or 0))
            self.requests += 1

    def record_cost(self, amount: float = 0.0) -> None:
        with self._lock:
            self.cost_usd += max(0.0, float(amount or 0.0))

    def mark(self, kind: str, amount: int = 1) -> None:
        with self._lock:
            if kind == "read":
                self.files_read += amount
            elif kind == "created":
                self.files_created += amount
            elif kind == "edited":
                self.files_edited += amount
            elif kind == "command":
                self.commands += amount

    def merge(self, other: "UsageStats") -> None:
        with self._lock:
            self.prompt_tokens += other.prompt_tokens
            self.completion_tokens += other.completion_tokens
            self.total_tokens += other.total_tokens
            self.requests += other.requests
            self.files_read += other.files_read
            self.files_created += other.files_created
            self.files_edited += other.files_edited
            self.commands += other.commands
        self.cost_usd += other.cost_usd

    def reset(self) -> None:
        with self._lock:
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
            "cache_hit_tokens": self.cache_hit_tokens,
            "cache_miss_tokens": self.cache_miss_tokens,
            "requests": self.requests,
            "files_read": self.files_read,
            "files_created": self.files_created,
            "files_edited": self.files_edited,
            "commands": self.commands,
            "cost_usd": self.cost_usd,
            "started_at": self.started_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UsageStats":
        stats = cls()
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "cache_hit_tokens",
            "cache_miss_tokens",
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
        try:
            stats.cost_usd = max(0.0, float(data.get("cost_usd", 0.0) or 0.0))
        except (TypeError, ValueError):
            stats.cost_usd = 0.0
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
            f"cache {self.cache_hit_tokens}/{self.cache_miss_tokens} "
            f"req {self.requests} "
            f"files r{self.files_read} c{self.files_created} e{self.files_edited} "
            f"cmds {self.commands} cost ${self.cost_usd:.4f}"
        )

    def detailed(self) -> str:
        elapsed = int((datetime.now() - self.started_at).total_seconds())
        return "\n".join(
            [
                f"Prompt tokens: {self.prompt_tokens}",
                f"Completion tokens: {self.completion_tokens}",
                f"Total tokens: {self.total_tokens}",
                f"Cache hit tokens: {self.cache_hit_tokens}",
                f"Cache miss tokens: {self.cache_miss_tokens}",
                f"Requests: {self.requests}",
                f"Files read: {self.files_read}",
                f"Files created: {self.files_created}",
                f"Files edited: {self.files_edited}",
                f"Commands run: {self.commands}",
                f"Estimated cost: ${self.cost_usd:.4f}",
                f"Elapsed: {elapsed}s",
            ]
        )
