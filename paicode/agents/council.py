import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..agent.events import AgentPhase, AgentStatus
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from .contract import BuildContract
from .json_utils import extract_json
from .prompts import (
    contract_review_prompt,
    finalize_prompt,
    proposal_prompt,
    repo_snapshot,
    synthesis_prompt,
)
from .roles import ROSTER, AgentRole, role_for
from .store import AgentStore


class CouncilError(RuntimeError):
    pass


def _emit(emit, event) -> None:
    try:
        emit(event)
    except Exception:
        pass


def parallel_map(items, worker, max_workers: int, stop_event=None) -> list:
    if not items:
        return []
    results = []
    workers = max(1, min(int(max_workers), len(items)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="paicode-agent") as pool:
        futures = {pool.submit(worker, item): item for item in items}
        for future in as_completed(futures):
            if stop_event is not None and stop_event.is_set():
                for pending in futures:
                    pending.cancel()
                break
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"error": f"{type(exc).__name__}: {exc}", "agent": getattr(futures[future], "id", 0)})
    return results


def _ask_json(client: ProviderClient, stats: UsageStats, prompt: str) -> dict:
    result = client.stream([{"role": "user", "content": prompt}], None)
    stats.record_usage(result.usage.prompt_tokens, result.usage.completion_tokens, result.usage.total_tokens)
    if not (result.text or "").strip():
        raise CouncilError("Model returned an empty council response.")
    return extract_json(result.text)


class Council:
    def __init__(
        self,
        root,
        provider: ProviderConfig,
        client: ProviderClient,
        stats: UsageStats,
        store: AgentStore,
        session_id: str,
        emit,
        stop_event,
        concurrency: int = 20,
        rules_text: str = "",
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
        self.rules_text = rules_text
        self.proposals: list[dict] = []
        self.reviews: list[dict] = []
        self.contract: BuildContract | None = None

    def _role_prompt(self, role: AgentRole, request: str, context: str) -> dict:
        run_id = self.store.create_run(
            self.session_id,
            role.id,
            role.title,
            "council-proposal",
            model=self.provider.model,
        )
        try:
            payload = _ask_json(self.client, self.stats, proposal_prompt(role, request, context, self.rules_text))
            payload.setdefault("agent", role.id)
            payload.setdefault("role", role.title)
            self.store.add_message(
                run_id, self.session_id, role.id, "council-proposal", "proposal",
                json.dumps(payload, ensure_ascii=False),
            )
            self.store.finish_run(run_id, "done", str(payload.get("understanding", ""))[:2000])
            _emit(self.emit, AgentStatus(role.id, role.title, "council-proposal", "done", str(payload.get("understanding", ""))[:200]))
            return payload
        except Exception as exc:
            self.store.finish_run(run_id, "failed", error=f"{type(exc).__name__}: {exc}")
            raise

    def _review(self, role: AgentRole, request: str) -> dict:
        assert self.contract is not None
        run_id = self.store.create_run(
            self.session_id,
            role.id,
            role.title,
            "council-review",
            model=self.provider.model,
        )
        try:
            payload = _ask_json(
                self.client,
                self.stats,
                contract_review_prompt(role, request, self.contract, self.rules_text),
            )
            payload.setdefault("agent", role.id)
            payload.setdefault("verdict", "approve")
            verdict = str(payload.get("verdict", "approve")).lower()
            changes = payload.get("required_changes", [])
            detail = "; ".join(str(item) for item in changes)[:1_500] if verdict == "object" else ""
            self.store.add_message(
                run_id, self.session_id, role.id, "council-review", "review",
                json.dumps(payload, ensure_ascii=False),
            )
            self.store.finish_run(run_id, "done", detail or verdict)
            _emit(self.emit, AgentStatus(role.id, role.title, "council-review", verdict, detail))
            return payload
        except Exception as exc:
            self.store.finish_run(run_id, "failed", error=f"{type(exc).__name__}: {exc}")
            raise

    def run(self, request: str) -> BuildContract:
        context = repo_snapshot(self.root)
        _emit(self.emit, AgentPhase("council", "proposal round", 0, len(ROSTER)))
        self.proposals = parallel_map(
            ROSTER,
            lambda role: self._role_prompt(role, request, context),
            self.concurrency,
            self.stop_event,
        )
        self.proposals = [item for item in self.proposals if "error" not in item]
        if not self.proposals:
            raise CouncilError("Every council proposal failed.")
        if self.stop_event.is_set():
            raise CouncilError("Stopped by user.")

        _emit(self.emit, AgentPhase("council", "lead synthesis", 0, 1))
        run_id = self.store.create_run(
            self.session_id, 1, role_for(1).title, "council-synthesis", model=self.provider.model
        )
        contract_payload = _ask_json(
            self.client,
            self.stats,
            synthesis_prompt(request, context, self.proposals, self.rules_text),
        )
        self.contract = BuildContract.from_dict(contract_payload)
        errors = self.contract.validate()
        if errors:
            repair = synthesis_prompt(
                request,
                context,
                [{"agent": "validation", "errors": errors, "previous": contract_payload}],
                self.rules_text,
            )
            contract_payload = _ask_json(self.client, self.stats, repair)
            self.contract = BuildContract.from_dict(contract_payload)
            errors = self.contract.validate()
        if errors:
            self.store.finish_run(run_id, "failed", error="; ".join(errors))
            raise CouncilError("Contract validation failed: " + "; ".join(errors))
        self.store.add_message(
            run_id, self.session_id, 1, "council-synthesis", "contract",
            json.dumps(self.contract.to_dict(), ensure_ascii=False),
        )
        self.store.finish_run(run_id, "done", self.contract.feature)
        _emit(self.emit, AgentStatus(1, role_for(1).title, "council-synthesis", "done", self.contract.feature))

        _emit(self.emit, AgentPhase("council", "contract review", 0, len(ROSTER)))
        self.reviews = parallel_map(
            ROSTER,
            lambda role: self._review(role, request),
            self.concurrency,
            self.stop_event,
        )
        self.reviews = [item for item in self.reviews if "error" not in item]
        objections = [
            item for item in self.reviews
            if str(item.get("verdict", "")).lower() == "object"
            or item.get("required_changes")
        ]
        summary = (
            f"{len(objections)} objection(s) resolved by the lead"
            if objections
            else "contract approved by all reviewers"
        )
        _emit(self.emit, AgentPhase("council", summary, len(self.reviews), len(ROSTER)))
        if objections and not self.stop_event.is_set():
            _emit(self.emit, AgentPhase("council", "lead arbitration", 0, 1))
            final_payload = _ask_json(
                self.client,
                self.stats,
                finalize_prompt(self.contract, self.reviews, self.rules_text),
            )
            final_contract = BuildContract.from_dict(final_payload)
            errors = final_contract.validate()
            if errors:
                raise CouncilError("Final contract validation failed: " + "; ".join(errors))
            self.contract = final_contract

        if self.stop_event.is_set():
            raise CouncilError("Stopped by user.")
        _emit(self.emit, AgentPhase("council", "contract frozen", len(self.reviews), len(ROSTER)))
        return self.contract
