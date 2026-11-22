from pathlib import Path

from ..agent.events import AgentAction, AgentPhase, AgentStatus, TextDelta, UsageUpdated
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from .contract import BuildContract
from .findings import BuildReport, ValidationResult
from .prompts import lead_report_prompt
from .roles import role_for
from .store import AgentStore


def _emit(emit, event) -> None:
    try:
        emit(event)
    except Exception:
        pass


class LeadReporter:
    def __init__(
        self,
        provider: ProviderConfig,
        client: ProviderClient,
        stats: UsageStats,
        store: AgentStore,
        session_id: str,
        emit,
        rules_text: str,
        stop_event=None,
    ):
        self.provider = provider
        self.client = client
        self.stats = stats
        self.store = store
        self.session_id = session_id
        self.emit = emit
        self.rules_text = rules_text
        self.stop_event = stop_event

    def _payload(
        self,
        contract: BuildContract,
        reports: dict[int, BuildReport],
        validation: ValidationResult | None,
        stopped: bool,
    ) -> dict:
        report_rows = [
            {
                "agent_id": report.agent_id,
                "status": report.status,
                "summary": report.summary,
                "files": report.files,
            }
            for report in reports.values()
        ]
        findings = [finding.to_dict() for finding in (validation.findings if validation else [])]
        status = "stopped" if stopped else ("passed" if validation and validation.ok else "failed")
        summary = validation.summary if validation else ("Stopped by user." if stopped else "No validation result.")
        return {
            "status": status,
            "summary": summary,
            "findings": findings,
            "reports": report_rows,
        }

    def _files(self, contract: BuildContract, reports: dict[int, BuildReport]) -> list[str]:
        found = {path for report in reports.values() for path in report.files}
        return sorted(found or set(contract.ownership()))

    def _deterministic(self, contract: BuildContract, payload: dict, files: list[str], stopped: bool) -> str:
        lines = [
            "## Summary",
            f"Lead report for **{contract.feature}**.",
            "",
            "## Delivered",
        ]
        if contract.work_units:
            for unit in contract.work_units:
                lines.append(f"- {unit.title} (`{', '.join(unit.files)}`) by agent {unit.owner}")
        else:
            lines.append("- No work units were assigned.")
        lines.extend(["", "## Validation", f"- Status: {payload['status']}", f"- {payload['summary']}"])
        lines.extend(["", "## Defects"])
        if payload["findings"]:
            for finding in payload["findings"]:
                lines.append(
                    f"- Agent {finding['owner']} [{finding['severity']}] {finding['title']} "
                    f"in `{finding['file'] or 'unknown'}`"
                )
        else:
            lines.append("- No open defects were reported.")
        lines.extend(["", "## Next steps"])
        if stopped:
            lines.append("- The run was stopped by the user. Resume with a narrower request.")
        elif payload["status"] == "passed":
            lines.append("- Review the changed files and run your normal project verification.")
        else:
            lines.append("- Resolve the open findings and rerun the validation suite.")
        lines.append(f"- Changed files: {', '.join(files) if files else 'none'}")
        return "\n".join(lines)

    def report(
        self,
        contract: BuildContract,
        reports: dict[int, BuildReport],
        validation: ValidationResult | None,
        stopped: bool = False,
    ) -> str:
        payload = self._payload(contract, reports, validation, stopped)
        files = self._files(contract, reports)
        fallback = self._deterministic(contract, payload, files, stopped)
        if stopped:
            _emit(self.emit, TextDelta("\n\n" + fallback + "\n"))
            return fallback
        _emit(self.emit, AgentPhase("report", "lead report", 0, 1))
        _emit(self.emit, AgentAction(1, role_for(1).title, "report", "writing final report", "running"))
        run_id = self.store.create_run(
            self.session_id, 1, role_for(1).title, "final-report", model=self.provider.model
        )
        prompt = lead_report_prompt(
            contract,
            payload["reports"],
            payload,
            files,
            self.stats.summary(),
            self.rules_text,
        )
        try:
            result = self.client.stream([{"role": "user", "content": prompt}], None, stop_event=self.stop_event)
            self.stats.record_usage(
                result.usage.prompt_tokens,
                result.usage.completion_tokens,
                result.usage.total_tokens,
            )
            _emit(self.emit, UsageUpdated(self.stats))
            text = (result.text or "").strip()
            if not text:
                raise RuntimeError("Lead report was empty.")
            self.store.add_message(run_id, self.session_id, 1, "final-report", "report", text)
            self.store.finish_run(run_id, "done", summary=text[:2000])
            _emit(self.emit, AgentAction(1, role_for(1).title, "report", "final report delivered", "done"))
            _emit(self.emit, AgentStatus(1, role_for(1).title, "final-report", "done", text[:220]))
            _emit(self.emit, TextDelta("\n\n" + text + "\n"))
            return text
        except Exception as exc:
            self.store.finish_run(
                run_id,
                "failed",
                summary=fallback[:2000],
                error=f"{type(exc).__name__}: {exc}",
            )
            _emit(self.emit, TextDelta("\n\n" + fallback + "\n"))
            return fallback
