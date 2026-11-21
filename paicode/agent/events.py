from dataclasses import dataclass, field


@dataclass
class TextDelta:
    text: str


@dataclass
class ReasoningDelta:
    text: str


@dataclass
class ToolStarted:
    name: str
    arguments: dict


@dataclass
class ToolFinished:
    name: str
    ok: bool
    output: str
    diff: str = ""
    changed: list[str] = field(default_factory=list)
    kind: str = ""


@dataclass
class UsageUpdated:
    stats: object


@dataclass
class Finished:
    message: str
    steps: int


@dataclass
class ErrorEvent:
    message: str


@dataclass
class AgentStatus:
    agent_id: int
    role: str
    phase: str
    status: str
    detail: str = ""
    files: list[str] = field(default_factory=list)
    tokens: int = 0


@dataclass
class AgentPhase:
    phase: str
    detail: str
    active: int = 0
    total: int = 0

