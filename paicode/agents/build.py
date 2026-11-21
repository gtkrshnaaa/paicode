import json
from pathlib import Path

from ..agent.events import AgentPhase, AgentStatus, ToolFinished, UsageUpdated
from ..agent.loop import AgentRunner
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from .contract import BuildContract, WorkUnit
from .council import _emit, parallel_map
from .findings import BuildReport, Finding
from .json_utils import extract_json
from .prompts import builder_system_prompt
from .roles import role_for
from .store import AgentStore


class BuildCoordinator:
    def __init__(
        self,
        root: Path,
        provider: ProviderConfig,
        client: ProviderClient,
        stats: UsageStats,
        store: AgentStore,
        session_id: str,
        emit,
        stop_event,
        concurrency: int = 20,
    ):
        self.root = root
        self.provider = provider
        self.client = client
        self.stats = stats
        self.store = store
        self.session_id = session_id
        self.emit = emit
        self.stop_event = stop_event
        self.concurrency = max(1, int(concurrency))
        self.reports: dict[int, BuildReport] = {}
        self.tasks: dict[int, str] = {}
        self.changes: list[tuple[str, str, list[str]]] = []

    def _brief(self, contract: BuildContract, units: list[WorkUnit], findings: list[Finding] | None) -> str:
        return builder_system_prompt(contract, units, findings=findings)

    def _run_builder(
        self,
        contract: BuildContract,
        owner: int,
        units: list[WorkUnit],
        task_id: str,
        phase: str,
        findings: list[Finding] | None = None,
    ) -> BuildReport:
        if self.stop_event.is_set():
            return BuildReport(owner, "stopped", "Stopped by user.", blockers=["stopped"])
        role = role_for(owner)
        run_id = self.store.create_run(
            self.session_id, owner, role.title, phase,
            parent_id=task_id, model=self.provider.model,
        )
        local_stats = UsageStats()
        changed: list[str] = []
        commands: list[str] = []

        def on_event(event) -> None:
            if isinstance(event, ToolFinished):
                changed.extend(event.changed)
                if event.diff:
                    self.changes.append((owner, event.diff, event.changed))
                if event.kind == "command":
                    commands.append(event.output.splitlines()[0] if event.output else "bash")
            elif isinstance(event, UsageUpdated):
                return

        allowed = {self.root / path for unit in units for path in unit.files}
        runner = AgentRunner(
            self.root,
            self.provider,
            local_stats,
            rules=[],
            skills=[],
            emit=on_event,
            max_steps=18,
            client=self.client,
            system_prompt=self._brief(contract, units, findings),
            allowed_write_paths=allowed,
            stop_event=self.stop_event,
        )
        error = ""
        try:
            final_text = runner.run(
                "Execute your assigned work units. Read the contract, write only your files, "
                "run the narrowest useful checks, then call finish with the required JSON report."
            )
        except Exception as exc:
            final_text = ""
            error = f"{type(exc).__name__}: {exc}"
        self.stats.merge(local_stats)
        _emit(self.emit, UsageUpdated(self.stats))

        status = "done"
        summary = final_text.strip()
        files = sorted(set(changed))
        blockers: list[str] = []
        if error:
            status = "failed"
            summary = error
        try:
            payload = extract_json(final_text)
        except Exception:
            payload = {}
        if payload:
            status = str(payload.get("status", status)).lower()
            summary = str(payload.get("summary", summary)).strip()
            files = [str(item) for item in payload.get("files", files)]
            commands = [str(item) for item in payload.get("commands", commands)]
            blockers = [str(item) for item in payload.get("blockers", [])]
        if self.stop_event.is_set():
            status = "stopped"
        report = BuildReport(owner, status, summary, files, commands, blockers)
        self.store.finish_run(
            run_id, status, summary=summary,
            usage=local_stats.to_dict(), error=error,
        )
        self.store.add_message(
            run_id, self.session_id, owner, phase, "report",
            json.dumps(report.__dict__, ensure_ascii=False),
        )
        self.store.update_task(task_id, status, report.__dict__)
        _emit(self.emit, AgentStatus(owner, role.title, phase, status, summary[:220], files, local_stats.total_tokens))
        owner_diffs = [
            (diff, changed_files)
            for changed_owner, diff, changed_files in self.changes
            if changed_owner == owner
        ]
        if owner_diffs:
            _emit(
                self.emit,
                ToolFinished(
                    name=f"agent {owner}",
                    ok=status == "done",
                    output=summary[:500],
                    diff="\n".join(item[0] for item in owner_diffs),
                    changed=sorted({path for _, paths in owner_diffs for path in paths}),
                    kind="edited",
                ),
            )
        return report

    def build(self, contract: BuildContract, contract_id: str) -> dict[int, BuildReport]:
        grouped = contract.builder_units()
        for owner, units in grouped.items():
            unit = WorkUnit(
                id="+".join(item.id for item in units),
                title=" / ".join(item.title for item in units),
                owner=owner,
                files=[path for item in units for path in item.files],
            )
            self.tasks[owner] = self.store.save_task(self.session_id, contract_id, unit)
        _emit(self.emit, AgentPhase("build", "parallel builders", 0, len(grouped)))
        results = parallel_map(
            list(grouped.items()),
            lambda item: self._run_builder(
                contract, item[0], item[1], self.tasks[item[0]], "build"
            ),
            min(self.concurrency, max(1, len(grouped))),
            self.stop_event,
        )
        for report in results:
            if isinstance(report, BuildReport):
                self.reports[report.agent_id] = report
            elif isinstance(report, dict) and "error" in report:
                _emit(self.emit, AgentStatus(0, "builder", "build", "failed", report["error"][:220]))
        _emit(self.emit, AgentPhase("build", "build complete", len(self.reports), len(grouped)))
        return self.reports

    def repair(self, contract: BuildContract, findings: list[Finding]) -> dict[int, BuildReport]:
        grouped = contract.builder_units()
        fallback_owner = next(iter(grouped), 1)
        by_owner: dict[int, list[Finding]] = {}
        for finding in findings:
            owner = finding.owner
            if owner not in grouped:
                owner = contract.ownership().get(finding.file, fallback_owner)
            by_owner.setdefault(owner, []).append(finding)
        repairs = []
        for owner, owner_findings in by_owner.items():
            units = grouped.get(owner)
            if not units:
                continue
            repairs.append((owner, units, owner_findings))
        if not repairs:
            return self.reports
        _emit(self.emit, AgentPhase("repair", "fixing findings", 0, len(repairs)))
        results = parallel_map(
            repairs,
            lambda item: self._run_builder(
                contract, item[0], item[1], self.tasks.get(item[0], ""), "repair", item[2]
            ),
            min(self.concurrency, max(1, len(repairs))),
            self.stop_event,
        )
        for report in results:
            if isinstance(report, BuildReport):
                self.reports[report.agent_id] = report
        return self.reports
