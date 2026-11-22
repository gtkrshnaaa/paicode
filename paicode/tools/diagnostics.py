import subprocess
from pathlib import Path

from .types import ToolResult


class DiagnosticsTools:
    def __init__(self, root: Path, commands: list[str]):
        self.root = root
        self.commands = commands

    def run(self, timeout: int = 120) -> ToolResult:
        if not self.commands:
            return ToolResult(True, "No diagnostics commands are configured.", kind="diagnostics")
        blocks = []
        ok = True
        for command in self.commands:
            try:
                completed = subprocess.run(
                    command,
                    shell=True,
                    cwd=str(self.root),
                    capture_output=True,
                    text=True,
                    timeout=max(1, int(timeout)),
                )
                output = ((completed.stdout or "") + (completed.stderr or "")).strip()
                status = "ok" if completed.returncode == 0 else f"exit {completed.returncode}"
                if completed.returncode != 0:
                    ok = False
                blocks.append(f"$ {command}\n[{status}]\n{output[:20_000]}")
            except subprocess.TimeoutExpired:
                ok = False
                blocks.append(f"$ {command}\n[timeout after {timeout}s]")
            except OSError as exc:
                ok = False
                blocks.append(f"$ {command}\n[error: {exc}]")
        return ToolResult(ok, "\n\n".join(blocks), kind="diagnostics")
