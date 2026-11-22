import threading
from datetime import datetime
from pathlib import Path

from ..agent.events import AgentAction, AgentPhase, ErrorEvent, TextDelta, UsageUpdated
from ..agent.loop import AgentRunner
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from ..rules.loader import render_rules
from .discussion import DiscussionRunner
from .json_utils import extract_json
from .prompts import repo_snapshot, triage_prompt
from .roles import role_for
from .runner import MultiAgentRunner

READ_INTENTS = {"discussion", "analysis", "summary", "audit", "plan", "review"}
WRITE_INTENTS = {"write", "fix", "refactor", "scaffold", "implement", "build", "feature"}
TEAM_KEYWORDS = {"scaffold", "feature", "migration", "redesign", "multi-module", "architecture"}
WRITE_VERBS = {
    "add", "create", "build", "implement", "fix", "update", "change", "refactor",
    "remove", "delete", "rename", "move", "scaffold", "migrate", "write",
}


def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


class SmartRunner:
    def __init__(
        self,
        root: Path,
        provider: ProviderConfig,
        stats: UsageStats,
        rules,
        skills,
        emit,
        session_id: str = "",
        concurrency: int | None = None,
        validation_rounds: int | None = None,
    ):
        self.root = root
        self.provider = provider
        self.stats = stats
        self.rules = rules
        self.rules_text = render_rules(rules)
        self.skills = skills
        self.emit = emit
        self.session_id = session_id
        self.concurrency = concurrency
        self.validation_rounds = validation_rounds
        self.client = ProviderClient(provider, max_concurrency=1)
        self.inner = None
        self.mode = "idle"
        self.reason = ""
        self.finished = False
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        self._stop_event.set()
        if hasattr(self.inner, "request_stop"):
            self.inner.request_stop()

    def _action(self, kind: str, detail: str, status: str = "running") -> None:
        self._emit(AgentAction(1, role_for(1).title, kind, detail, status, _stamp()))

    def _emit(self, event) -> None:
        try:
            self.emit(event)
        except Exception:
            pass

    def _decide(self, payload: dict, request: str) -> tuple[str, int, str]:
        intent = str(payload.get("intent", "")).strip().lower()
        mode = str(payload.get("mode", "")).strip().lower()
        try:
            expected = int(payload.get("expected_files", 0) or 0)
        except (TypeError, ValueError):
            expected = 0
        reason = str(payload.get("reason", "")).strip() or "lead routing decision"
        lowered = request.lower()

        if intent in READ_INTENTS:
            mode = "discussion"
        elif intent in WRITE_INTENTS:
            if expected > 1 or expected <= 0:
                mode = "team"
            elif intent in {"scaffold", "feature"}:
                mode = "team"
            elif any(word in lowered for word in TEAM_KEYWORDS):
                mode = "team"
            else:
                mode = "single"
        elif mode not in {"single", "discussion", "team"}:
            write_like = any(word in lowered.split() for word in WRITE_VERBS)
            mode = "team" if write_like else "discussion"

        if mode == "team" and intent in READ_INTENTS:
            mode = "discussion"
        if mode == "single" and expected > 1:
            mode = "team"
        if mode == "single" and expected <= 0:
            mode = "team"
        if mode == "discussion" and intent in WRITE_INTENTS:
            mode = "team" if expected != 1 else "single"
        return mode, expected, reason

    def _fallback_decision(self, request: str) -> tuple[str, int, str]:
        lowered = request.lower()
        write_like = any(word in lowered.split() for word in WRITE_VERBS)
        if any(word in lowered for word in ("explain", "summar", "audit", "plan", "discuss", "review")):
            return "discussion", 0, "fallback: read-only request"
        if write_like:
            return "team", 0, "fallback: write work defaults to team"
        return "discussion", 0, "fallback: unknown request defaults to read-only"

    def _triage(self, request: str) -> tuple[str, int, str]:
        context = repo_snapshot(self.root)
        self._action("think", "reading the request and repository context")
        try:
            result = self.client.stream(
                [{"role": "user", "content": triage_prompt(request, context, self.rules_text)}],
                None,
                stop_event=self._stop_event,
            )
            self.stats.record_usage(
                result.usage.prompt_tokens,
                result.usage.completion_tokens,
                result.usage.total_tokens,
            )
            self._emit(UsageUpdated(self.stats))
            payload = extract_json(result.text or "")
            return self._decide(payload, request)
        except Exception as exc:
            if self._stop_event.is_set():
                raise
            self._action("think", f"triage fallback: {type(exc).__name__}", "warning")
            return self._fallback_decision(request)

    def run(self, user_text: str, images=None) -> str:
        if self._stop_event.is_set():
            self._emit(ErrorEvent("Stopped by user."))
            return ""
        self._emit(AgentPhase("triage", "lead classification", 0, 1))
        try:
            mode, expected, reason = self._triage(user_text)
        except Exception:
            self._emit(ErrorEvent("Stopped by user."))
            return ""
        self.mode = mode
        self.reason = reason
        self._action("route", f"{mode}: {reason}", "done")
        files = f"{expected} expected file(s)" if expected else "unknown file count"
        self._emit(TextDelta(f"\n**Lead triage:** {mode}. {reason} ({files}).\n"))
        self._emit(AgentPhase("route", mode, 0, 1))
        if mode == "team":
            self.inner = MultiAgentRunner(
                self.root,
                self.provider,
                self.stats,
                self.rules,
                self.skills,
                emit=self.emit,
                session_id=self.session_id,
                concurrency=self.concurrency,
                validation_rounds=self.validation_rounds,
            )
        elif mode == "discussion":
            self.inner = DiscussionRunner(
                self.root, self.provider, self.stats, self.rules, self.skills, self.emit
            )
        else:
            self.inner = AgentRunner(
                self.root,
                self.provider,
                self.stats,
                self.rules,
                self.skills,
                emit=self.emit,
                max_steps=0,
                stop_event=self._stop_event,
            )
        result = self.inner.run(user_text, images=images)
        self.finished = True
        return result

    @property
    def contract(self):
        return getattr(self.inner, "contract", None)

    def agent_status(self) -> list[dict]:
        if hasattr(self.inner, "agent_status"):
            return self.inner.agent_status()
        return [
            {
                "agent_id": 1,
                "role": role_for(1).title,
                "phase": self.mode,
                "status": "done" if self.finished else "running",
                "summary": self.reason,
                "total_tokens": 0,
            }
        ]

    def latest_findings(self) -> list[dict]:
        if hasattr(self.inner, "latest_findings"):
            return self.inner.latest_findings()
        return []
