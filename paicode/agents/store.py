import json
from datetime import datetime
from uuid import uuid4

from ..db import Database
from .contract import BuildContract, WorkUnit
from .findings import Finding


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


class AgentStore:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.initialize()

    @property
    def path(self):
        return self.db.path

    def create_run(
        self,
        session_id: str,
        agent_id: int,
        role: str,
        phase: str,
        parent_id: str = "",
        model: str = "",
    ) -> str:
        run_id = _new_id("run")
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs
                    (id, session_id, agent_id, role, phase, status, parent_id, model, started_at)
                VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)
                """,
                (run_id, session_id, agent_id, role, phase, parent_id or None, model, _stamp()),
            )
        return run_id

    def finish_run(self, run_id: str, status: str, summary: str = "", usage=None, error: str = "") -> None:
        usage = usage or {}
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE agent_runs
                SET status = ?, summary = ?, error = ?, prompt_tokens = ?, completion_tokens = ?,
                    total_tokens = ?, finished_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    summary[:20_000],
                    error[:20_000],
                    int(usage.get("prompt_tokens", 0) or 0),
                    int(usage.get("completion_tokens", 0) or 0),
                    int(usage.get("total_tokens", 0) or 0),
                    _stamp(),
                    run_id,
                ),
            )

    def add_message(self, run_id: str, session_id: str, agent_id: int, phase: str, kind: str, content: str) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_messages
                    (run_id, session_id, agent_id, phase, kind, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, session_id, agent_id, phase, kind, content[:50_000], _stamp()),
            )

    def save_contract(self, session_id: str, contract: BuildContract, version: int = 1) -> str:
        contract_id = _new_id("contract")
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO build_contracts
                    (id, session_id, version, feature, contract_json, markdown, frozen, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    contract_id,
                    session_id,
                    version,
                    contract.feature,
                    json.dumps(contract.to_dict(), ensure_ascii=False),
                    contract.markdown(),
                    _stamp(),
                ),
            )
            for path, agent_id in contract.ownership().items():
                conn.execute(
                    "INSERT OR REPLACE INTO file_ownership (session_id, contract_id, path, agent_id) VALUES (?, ?, ?, ?)",
                    (session_id, contract_id, path, agent_id),
                )
        return contract_id

    def latest_contract(self, session_id: str) -> BuildContract | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT contract_json FROM build_contracts WHERE session_id = ? ORDER BY version DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return BuildContract.from_dict(json.loads(row["contract_json"]))

    def latest_contract_id(self, session_id: str) -> str:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id FROM build_contracts WHERE session_id = ? ORDER BY version DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        return row["id"] if row else ""

    def save_task(self, session_id: str, contract_id: str, unit: WorkUnit) -> str:
        task_id = _new_id("task")
        stamp = _stamp()
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_tasks
                    (id, session_id, contract_id, agent_id, title, files_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    task_id,
                    session_id,
                    contract_id,
                    unit.owner,
                    unit.title,
                    json.dumps(unit.files),
                    stamp,
                    stamp,
                ),
            )
        return task_id

    def update_task(self, task_id: str, status: str, report: dict | None = None) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE agent_tasks SET status = ?, report_json = ?, updated_at = ? WHERE id = ?",
                (status, json.dumps(report or {}, ensure_ascii=False), _stamp(), task_id),
            )

    def create_validation(self, session_id: str, contract_id: str, round_number: int) -> str:
        validation_id = _new_id("val")
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO validation_runs
                    (id, session_id, contract_id, round_number, status, summary, started_at)
                VALUES (?, ?, ?, ?, 'running', '', ?)
                """,
                (validation_id, session_id, contract_id, round_number, _stamp()),
            )
        return validation_id

    def finish_validation(self, validation_id: str, status: str, summary: str, findings: list[Finding]) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE validation_runs SET status = ?, summary = ?, findings_count = ?, finished_at = ? WHERE id = ?",
                (status, summary[:20_000], len(findings), _stamp(), validation_id),
            )
            for finding in findings:
                conn.execute(
                    """
                    INSERT INTO validation_findings
                        (validation_id, session_id, owner, severity, title, file, line, expected,
                         actual, command, fix, message, status, created_at)
                    VALUES (?, (SELECT session_id FROM validation_runs WHERE id = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                    """,
                    (
                        validation_id,
                        validation_id,
                        finding.owner,
                        finding.severity,
                        finding.title,
                        finding.file,
                        finding.line,
                        finding.expected,
                        finding.actual,
                        finding.command,
                        finding.fix,
                        finding.message,
                        _stamp(),
                    ),
                )
            if status == "passed":
                conn.execute(
                    """
                    UPDATE validation_findings SET status = 'resolved'
                    WHERE session_id = (SELECT session_id FROM validation_runs WHERE id = ?)
                      AND status = 'open'
                    """,
                    (validation_id,),
                )

    def add_strike(self, session_id: str, agent_id: int, reason: str) -> int:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO agent_strikes (session_id, agent_id, reason, created_at) VALUES (?, ?, ?, ?)",
                (session_id, agent_id, reason[:5_000], _stamp()),
            )
            row = conn.execute(
                "SELECT COUNT(*) FROM agent_strikes WHERE session_id = ? AND agent_id = ?",
                (session_id, agent_id),
            ).fetchone()
        return int(row[0])

    def strike_count(self, session_id: str, agent_id: int) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM agent_strikes WHERE session_id = ? AND agent_id = ?",
                (session_id, agent_id),
            ).fetchone()
        return int(row[0])

    def add_event(self, session_id: str, agent_id: int, phase: str, kind: str, detail: str = "") -> None:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO agent_events (session_id, agent_id, phase, kind, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, agent_id, phase, kind, detail[:20_000], _stamp()),
            )

    def agent_status(self, session_id: str) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT agent_id, role, phase, status, summary, total_tokens, started_at, finished_at
                FROM agent_runs WHERE session_id = ? ORDER BY started_at DESC, id DESC
                """,
                (session_id,),
            ).fetchall()
        latest: dict[int, dict] = {}
        for row in rows:
            latest.setdefault(int(row["agent_id"]), dict(row))
        return [latest[key] for key in sorted(latest)]

    def latest_findings(self, session_id: str) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM validation_findings WHERE session_id = ? ORDER BY id DESC LIMIT 100",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]
