from dataclasses import dataclass, field


@dataclass
class ToolResult:
    ok: bool
    output: str
    diff: str = ""
    changed: list[str] = field(default_factory=list)
    kind: str = ""
