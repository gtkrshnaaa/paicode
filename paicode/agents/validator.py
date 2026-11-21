from pathlib import Path

from ..agent.events import AgentPhase, AgentStatus, UsageUpdated
from ..agent.loop import AgentRunner
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from ..tools.shell import ShellTools
from .contract import BuildContract
from .council import _emit
from .findings import Finding, ValidationResult
from .json_utils import extract_json
from .prompts import validator_system_prompt
from .roles import role_for
from .store import AgentStore


class Validator:
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
    ):
        self.root = root
        self.provider = provider
        self.client = client
        self.stats = stats
        self.store = store
        self.session_id = session_id
        self.emit = emit
        self.stop_event = stop_event

    def _precheck(self, contract: BuildContract) -> tuple[bool, str, list[Finding]]:
        findings: list[Finding] = []
        for path, owner in sorted(contract.ownership().items()):
            if not (self.root / path).is_file():
                findings.append(
                    Finding(
                        owner=owner,
                        severity="critical",
                        title=f"Missing owned file: {path}",
                        file=path,
                        expected="File exists and matches the contract",
                        actual="File is missing",
                        command=f"test -f {path}",
                        fix=f"Create {path} and complete {role_for(owner).title} work",
                        message=f"Agent {owner}, {path} is missing. This is a contract violation. Create it and report back.",
                    )
                )
        command = contract.commands.get("test", "").strip()
        output = ""
        ok = not findings
        if command:
            shell = ShellTools(self.root, self.stats, timeout=180, stop_event=self.stop_event)
            try:
                result = shell.run(command, timeout=180)
                output = f"$ {command}\n{result.output}"
                if not result.ok:
                    ok = False
            except Exception as exc:
                output = f"$ {command}\nError: {type(exc).__name__}: {exc}"
                ok = False
        return ok, output[-20_000:], findings

    def validate(self, contract: BuildContract, contract_id: str, round_number: int) -> ValidationResult:
        validation_id = self.store.create_validation(
            self.session_id, contract_id, round_number
        )
        _emit(self.emit, AgentPhase("validate", f"round {round_number}", 0, 1))
        precheck_ok, precheck_output, precheck_findings = self._precheck(contract)
        run_id = self.store.create_run(
            self.session_id, 22, role_for(22).title, "validation",
            model=self.provider.model,
        )
        local_stats = UsageStats()

        def on_event(event) -> None:
            if isinstance(event, UsageUpdated):
                return

        prompt = (
            validator_system_prompt(contract)
            + "\n\nDeterministic precheck output:\n"
            + (precheck_output or "No test command was configured.")
            + "\n\nValidate the integrated workspace now. Return JSON through finish."
        )
        runner = AgentRunner(
            self.root,
            self.provider,
            local_stats,
            rules=[],
            skills=[],
            emit=on_event,
            max_steps=24,
            client=self.client,
            system_prompt=prompt,
            allowed_write_paths=set(),
        )
        error = ""
        try:
            final_text = runner.run(
                "Run the validation contract. Inspect files, run tests and acceptance checks, "
                "audit ownership, and finish with the required JSON."
            )
        except Exception as exc:
            final_text = ""
            error = f"{type(exc).__name__}: {exc}"
        self.stats.merge(local_stats)
        _emit(self.emit, UsageUpdated(self.stats))

        payload = {}
        try:
            payload = extract_json(final_text)
        except Exception:
            payload = {}
        findings = list(precheck_findings)
        for item in payload.get("findings", []) if isinstance(payload.get("findings"), list) else []:
            if isinstance(item, dict):
                findings.append(Finding.from_dict(item))
        for finding in findings:
            if finding.owner <= 0 or finding.owner > 22:
                finding.owner = contract.ownership().get(finding.file, 1)
        if not precheck_ok and not findings:
            findings.append(
                Finding(
                    owner=1,
                    severity="critical",
                    title="Configured test command failed",
                    command=contract.commands.get("test", ""),
                    actual=precheck_output[-4_000:],
                    fix="Make the configured test command pass.",
                    message="The configured test command is failing. The owning builders must fix it.",
                )
            )
        ok = bool(payload.get("ok", precheck_ok)) and precheck_ok and not findings
        summary = str(payload.get("summary", "")).strip()
        if error:
            summary = error
            ok = False
        if not summary:
            summary = "Validation passed." if ok else "Validation failed."
        commands = [str(item) for item in payload.get("commands", [])] if isinstance(payload.get("commands"), list) else []
        if precheck_output:
            commands.insert(0, precheck_output)
        status = "passed" if ok else "failed"
        self.store.finish_run(
            run_id, status, summary=summary, usage=local_stats.to_dict(), error=error
        )
        self.store.finish_validation(validation_id, status, summary, findings)
        _emit(
            self.emit,
            AgentStatus(
                22,
                role_for(22).title,
                "validation",
                status,
                summary[:220],
                tokens=local_stats.total_tokens,
            ),
        )
        return ValidationResult(ok=ok, summary=summary, findings=findings, commands=commands)
