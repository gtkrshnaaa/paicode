from dataclasses import dataclass, field


@dataclass
class Finding:
    owner: int
    severity: str
    title: str
    file: str = ""
    line: int = 0
    expected: str = ""
    actual: str = ""
    command: str = ""
    fix: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "owner": self.owner,
            "severity": self.severity,
            "title": self.title,
            "file": self.file,
            "line": self.line,
            "expected": self.expected,
            "actual": self.actual,
            "command": self.command,
            "fix": self.fix,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Finding":
        try:
            owner = int(data.get("owner", 0) or 0)
        except (TypeError, ValueError):
            owner = 0
        try:
            line = int(data.get("line", 0) or 0)
        except (TypeError, ValueError):
            line = 0
        return cls(
            owner=owner,
            severity=str(data.get("severity", "major")).strip().lower(),
            title=str(data.get("title", "")).strip() or "Validation failure",
            file=str(data.get("file", "")).strip(),
            line=line,
            expected=str(data.get("expected", "")).strip(),
            actual=str(data.get("actual", "")).strip(),
            command=str(data.get("command", "")).strip(),
            fix=str(data.get("fix", "")).strip(),
            message=str(data.get("message", "")).strip(),
        )


@dataclass
class BuildReport:
    agent_id: int
    status: str
    summary: str
    files: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    ok: bool
    summary: str
    findings: list[Finding] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
