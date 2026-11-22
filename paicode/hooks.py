import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .settings import Hook, Settings, load_settings


MAX_HOOK_OUTPUT = 8_000


def _hook_environment() -> dict[str, str]:
    env = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(part in upper for part in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")):
            continue
        env[key] = value
    return env


@dataclass
class HookOutcome:
    allowed: bool = True
    reasons: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    def deny(self, reason: str) -> None:
        self.allowed = False
        self.reasons.append(reason)


class HookRunner:
    def __init__(self, root: Path, settings: Settings | None = None):
        self.root = root
        self.settings = settings or load_settings(root)

    def run(self, event: str, payload: dict, blocking: bool = False) -> HookOutcome:
        outcome = HookOutcome()
        hooks = [hook for hook in self.settings.hooks if hook.enabled and hook.event == event]
        if not hooks:
            return outcome
        body = json.dumps({"event": event, "cwd": str(self.root), **payload}, ensure_ascii=False)
        for hook in hooks:
            result = self._run_one(hook, body)
            if result is None:
                if blocking:
                    outcome.deny(f"Hook for {event} timed out.")
                continue
            code, output = result
            if output:
                outcome.outputs.append(output[:MAX_HOOK_OUTPUT])
            if code == 0:
                continue
            reason = output.strip().splitlines()[-1] if output.strip() else f"exit code {code}"
            if blocking:
                outcome.deny(f"Hook for {event} blocked the call: {reason}")
        return outcome

    def _run_one(self, hook: Hook, body: str) -> tuple[int, str] | None:
        try:
            completed = subprocess.run(
                hook.command,
                shell=True,
                cwd=str(self.root),
                input=body,
                capture_output=True,
                text=True,
                timeout=hook.timeout,
                env=_hook_environment(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        output = (completed.stdout or "") + (completed.stderr or "")
        return completed.returncode, output.strip()
