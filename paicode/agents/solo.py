import os
from datetime import datetime
from pathlib import Path
from threading import Event

from ..agent.events import AgentAction, AgentPhase, ErrorEvent, Finished, TextDelta, UsageUpdated
from ..agent.loop import AgentRunner
from ..agent.prompts import build_system_prompt
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from ..settings import load_settings
from ..tools.diagnostics import DiagnosticsTools
from .discussion import DiscussionRunner
from .json_utils import extract_json
from .prompts import repo_snapshot
from .roles import role_for


SOLO_PROMPT = """

SOLO MODE IS ACTIVE.
You are one senior engineer working alone. Be thorough, but spend tokens deliberately.

Workflow:
1. Read the plan and inspect the smallest set of files needed.
2. Create a live checklist with the todo tool before editing.
3. Make surgical changes. Prefer edit over rewriting whole files.
4. Run the narrowest useful checks after each logical change.
5. Update the todo list as work completes.
6. Call finish with what changed, tests run, and remaining risks.

Rules:
- Do not delegate to another agent.
- Do not claim success without command output or file evidence.
- Keep explanations short. Do not restate the whole repository.
- Do not reread large unchanged files.
- If a check fails, diagnose the root cause before editing again.
"""


def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


class SoloRunner:
    def __init__(
        self,
        root: Path,
        provider: ProviderConfig,
        stats: UsageStats,
        rules,
        skills,
        emit,
        session_id: str = "",
        history: list[dict] | None = None,
        max_steps: int | None = None,
    ):
        self.root = root
        self.provider = provider
        self.stats = stats
        self.rules = rules
        self.skills = skills
        self.emit = emit
        self.session_id = session_id
        self.history = history or []
        if max_steps is None or int(max_steps) <= 0:
            try:
                max_steps = int(os.getenv("PAICODE_SOLO_MAX_STEPS", "60") or 60)
            except ValueError:
                max_steps = 60
        self.max_steps = max(1, int(max_steps))
        self.settings = load_settings(root)
        self.client = ProviderClient(provider, max_concurrency=1)
        self._stop_event = Event()
        self.mode = "solo"
        self.finished = False
        self.plan: dict = {}
        self.messages: list[dict] = []

    def request_stop(self) -> None:
        self._stop_event.set()

    def _emit_event(self, event) -> None:
        try:
            self.emit(event)
        except Exception:
            pass

    def _action(self, kind: str, detail: str, status: str = "running") -> None:
        self._emit_event(AgentAction(1, role_for(1).title, kind, detail, status, _stamp()))

    def _inner_emit(self, event) -> None:
        if isinstance(event, Finished):
            return
        self._emit_event(event)

    def _record(self, result) -> None:
        self.stats.record_usage(
            result.usage.prompt_tokens,
            result.usage.completion_tokens,
            result.usage.total_tokens,
            result.usage.cache_hit_tokens,
            result.usage.cache_miss_tokens,
        )
        self.stats.record_cost(
            self.settings.budget.cost_detailed(
                result.usage.prompt_tokens,
                result.usage.completion_tokens,
                result.usage.cache_hit_tokens,
                result.usage.cache_miss_tokens,
            )
        )
        self._emit_event(UsageUpdated(self.stats))

    def _plan(self, user_text: str) -> dict:
        self._emit_event(AgentPhase("plan", "solo planning", 0, 1))
        self._action("think", "planning the smallest reliable path")
        context = repo_snapshot(self.root)
        prompt = (
            "Plan a single-agent coding task. Return JSON only with keys: "
            '{"read_only": boolean, "goal": string, "steps": [string], '
            '"files": [string], "risks": [string]}. '
            "Mark read_only true only when the request is explanation, review, audit, or planning "
            "with no file changes. Keep steps to 3-8 concrete actions.\\n\\n"
            f"Request:\\n{user_text}\\n\\nRepository context:\\n{context}"
        )
        result = self.client.stream(
            [{"role": "user", "content": prompt}],
            [],
            stop_event=self._stop_event,
            max_tokens=1200,
        )
        self._record(result)
        try:
            plan = extract_json(result.text or "")
        except Exception:
            plan = {"read_only": False, "goal": user_text, "steps": [], "files": [], "risks": []}
        return plan

    def _system_prompt(self, plan: dict) -> str:
        steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
        files = plan.get("files", []) if isinstance(plan.get("files"), list) else []
        risks = plan.get("risks", []) if isinstance(plan.get("risks"), list) else []
        lines = [
            build_system_prompt(self.root, self.rules, self.skills),
            SOLO_PROMPT,
            "",
            "APPROVED PLAN",
            f"Goal: {plan.get('goal', '')}",
        ]
        lines.extend(f"- {item}" for item in steps if str(item).strip())
        if files:
            lines.append("Likely files:")
            lines.extend(f"- {item}" for item in files if str(item).strip())
        if risks:
            lines.append("Known risks:")
            lines.extend(f"- {item}" for item in risks if str(item).strip())
        return "\n".join(lines)

    def _diagnostics(self) -> tuple[bool, str]:
        if not self.settings.diagnostics:
            return True, ""
        self._emit_event(AgentPhase("verify", "running diagnostics", 0, 1))
        self._action("command", "running configured diagnostics")
        result = DiagnosticsTools(self.root, self.settings.diagnostics).run()
        self._action("command", "diagnostics passed" if result.ok else "diagnostics failed", "done" if result.ok else "failed")
        return result.ok, result.output

    def run(self, user_text: str, images=None) -> str:
        if self._stop_event.is_set():
            self._emit_event(ErrorEvent("Stopped by user."))
            return ""
        try:
            self.plan = self._plan(user_text)
        except Exception as exc:
            if self._stop_event.is_set():
                self._emit_event(ErrorEvent("Stopped by user."))
                return ""
            self.plan = {"read_only": False, "goal": user_text, "steps": [], "files": [], "risks": []}
            self._action("think", f"planning fallback: {type(exc).__name__}", "warning")

        if self.plan.get("read_only"):
            self.mode = "discussion"
            self._emit_event(AgentPhase("route", "read-only discussion", 0, 1))
            runner = DiscussionRunner(
                self.root, self.provider, self.stats, self.rules, self.skills, self.emit
            )
            result = runner.run(user_text, images=images)
            self.finished = True
            return result

        self.mode = "solo"
        steps = self.plan.get("steps", []) if isinstance(self.plan.get("steps"), list) else []
        self._emit_event(AgentPhase("act", f"solo plan with {len(steps)} step(s)", 0, 1))
        self._action("route", "solo mode", "done")
        self._emit_event(
            TextDelta(
                "\n**Solo plan:** "
                + ("; ".join(str(item) for item in steps[:6]) if steps else "inspect, edit, verify")
                + "\n"
            )
        )
        runner = AgentRunner(
            self.root,
            self.provider,
            self.stats,
            self.rules,
            self.skills,
            emit=self._inner_emit,
            max_steps=self.max_steps,
            history=self.history,
            client=self.client,
            system_prompt=self._system_prompt(self.plan),
            stop_event=self._stop_event,
        )
        text = runner.run(user_text, images=images)
        self.messages = runner.messages

        if self._stop_event.is_set():
            self.finished = True
            return text

        if self.settings.diagnostics and (self.stats.files_edited or self.stats.files_created):
            ok, output = self._diagnostics()
            if not ok:
                self._emit_event(TextDelta("\nDiagnostics failed. Running one bounded repair pass.\n"))
                repair_prompt = (
                    self._system_prompt(self.plan)
                    + "\n\nDIAGNOSTICS FAILED\n"
                    + output[-12_000:]
                    + "\nFix the root cause, rerun the narrowest check, then call finish."
                )
                repair = AgentRunner(
                    self.root,
                    self.provider,
                    self.stats,
                    self.rules,
                    self.skills,
                    emit=self._inner_emit,
                    max_steps=min(20, self.max_steps),
                    client=self.client,
                    system_prompt=repair_prompt,
                    stop_event=self._stop_event,
                )
                repair_text = repair.run("Repair the failing diagnostics.")
                self.messages = repair.messages
                ok, output = self._diagnostics()
                text = (text + "\n\n" + repair_text).strip()
                if not ok:
                    self._emit_event(TextDelta("\nDiagnostics still failing after one repair pass.\n"))
            else:
                self._emit_event(TextDelta("\nDiagnostics passed.\n"))

        self.finished = True
        self._emit_event(Finished(text or "Task finished.", 1))
        return text

    def agent_status(self) -> list[dict]:
        return [
            {
                "agent_id": 1,
                "role": role_for(1).title,
                "phase": self.mode,
                "status": "done" if self.finished else "running",
                "summary": str(self.plan.get("goal", "")),
                "total_tokens": self.stats.total_tokens,
            }
        ]

    def latest_findings(self) -> list[dict]:
        return []

    @property
    def contract(self):
        return None
