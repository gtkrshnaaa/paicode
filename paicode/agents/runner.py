import os
import queue
import threading
from pathlib import Path
from uuid import uuid4

from ..agent.events import AgentPhase, ErrorEvent, Finished, TextDelta
from ..agent.loop import AgentRunner
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from ..rules.loader import render_rules
from .build import BuildCoordinator
from .council import Council, CouncilError, _emit
from .findings import ValidationResult
from .report import LeadReporter
from .store import AgentStore
from .validator import Validator


class MultiAgentRunner:
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
        self._user_emit = emit
        self._event_queue: queue.Queue = queue.Queue()
        self._event_stop = object()
        self._event_thread = threading.Thread(
            target=self._dispatch_events, name="paicode-events", daemon=True
        )
        self._event_thread.start()
        self.emit = self._enqueue
        self.session_id = session_id or f"run-{uuid4().hex[:8]}"
        self.concurrency = concurrency or int(os.getenv("PAICODE_AGENT_CONCURRENCY", "22") or 22)
        self.concurrency = max(1, min(22, self.concurrency))
        self.validation_rounds = validation_rounds or int(os.getenv("PAICODE_VALIDATION_ROUNDS", "5") or 5)
        self.validation_rounds = max(1, self.validation_rounds)
        self.max_strikes = max(1, int(os.getenv("PAICODE_AGENT_STRIKES", "3") or 3))
        self.store = AgentStore()
        self.client = ProviderClient(provider, max_concurrency=self.concurrency)
        self._stop_event = threading.Event()
        self.contract = None
        self.contract_id = ""
        self.reports: dict = {}
        self.last_validation: ValidationResult | None = None
        self.phase = "idle"
        self.reporter = LeadReporter(
            provider,
            self.client,
            stats,
            self.store,
            self.session_id,
            self.emit,
            self.rules_text,
        )

    def _enqueue(self, event) -> None:
        self._event_queue.put(event)

    def _dispatch_events(self) -> None:
        while True:
            event = self._event_queue.get()
            if event is self._event_stop:
                self._event_queue.task_done()
                break
            try:
                self._user_emit(event)
            except Exception:
                pass
            finally:
                self._event_queue.task_done()

    def _flush_events(self) -> None:
        if not self._event_thread.is_alive():
            return
        self._event_queue.put(self._event_stop)
        self._event_thread.join(timeout=10)

    def request_stop(self) -> None:
        self._stop_event.set()

    def _phase(self, phase: str, detail: str, active: int = 0, total: int = 0) -> None:
        self.phase = phase
        _emit(self.emit, AgentPhase(phase, detail, active, total))

    def run(self, user_text: str, images=None) -> str:
        try:
            if images:
                return self._single_agent(user_text, images)
            try:
                return self._multi(user_text)
            except CouncilError as exc:
                if self._stop_event.is_set():
                    _emit(self.emit, ErrorEvent("Stopped by user."))
                    return ""
                self._phase("fallback", str(exc)[:300])
                return self._single_agent(user_text, None)
            except Exception as exc:
                _emit(self.emit, ErrorEvent(f"{type(exc).__name__}: {exc}"))
                return ""
        finally:
            self._flush_events()

    def _single_agent(self, user_text: str, images) -> str:
        runner = AgentRunner(
            self.root,
            self.provider,
            self.stats,
            self.rules,
            self.skills,
            emit=self.emit,
            stop_event=self._stop_event,
        )
        return runner.run(user_text, images=images)

    def _multi(self, user_text: str) -> str:
        _emit(self.emit, TextDelta("Council starting. 22 agents are reviewing the request."))
        council = Council(
            self.root,
            self.provider,
            self.client,
            self.stats,
            self.store,
            self.session_id,
            self.emit,
            self._stop_event,
            self.concurrency,
            self.rules_text,
        )
        self.contract = council.run(user_text)
        self.contract_id = self.store.save_contract(self.session_id, self.contract)
        active = len(self.contract.builder_units())
        _emit(
            self.emit,
            TextDelta(
                f"\nContract frozen: {self.contract.feature}. "
                f"{len(self.contract.work_units)} work units, {active} active builders, "
                f"{22 - active} builders idle.\n"
            ),
        )
        build = BuildCoordinator(
            self.root,
            self.provider,
            self.client,
            self.stats,
            self.store,
            self.session_id,
            self.emit,
            self._stop_event,
            self.concurrency,
            self.rules_text,
        )
        self.reports = build.build(self.contract, self.contract_id)
        validator = Validator(
            self.root,
            self.provider,
            self.client,
            self.stats,
            self.store,
            self.session_id,
            self.emit,
            self._stop_event,
            self.rules_text,
        )
        for round_number in range(1, self.validation_rounds + 1):
            if self._stop_event.is_set():
                break
            validation = validator.validate(self.contract, self.contract_id, round_number)
            self.last_validation = validation
            if validation.ok:
                break
            _emit(
                self.emit,
                TextDelta(
                    f"\nValidation round {round_number} found {len(validation.findings)} defect(s). "
                    "Sending them to the owning builders.\n"
                ),
            )
            if not validation.findings:
                break
            for finding in validation.findings:
                self.store.add_strike(self.session_id, finding.owner, finding.title)
            if any(
                self.store.strike_count(self.session_id, owner) >= self.max_strikes
                for owner in {finding.owner for finding in validation.findings}
            ):
                _emit(self.emit, TextDelta("\nA builder reached three strikes. The lead is taking over the repair.\n"))
                break
            build.repair(self.contract, validation.findings)
            self.reports = build.reports
        stopped = self._stop_event.is_set()
        final_summary = self._final_report(self.last_validation, stopped)
        _emit(self.emit, Finished("Report delivered.", max(1, self.stats.requests)))
        return final_summary

    def _final_report(self, validation: ValidationResult | None, stopped: bool) -> str:
        self.reporter.emit = self.emit
        return self.reporter.report(self.contract, self.reports, validation, stopped)

    def agent_status(self) -> list[dict]:
        return self.store.agent_status(self.session_id)

    def latest_findings(self) -> list[dict]:
        return self.store.latest_findings(self.session_id)
