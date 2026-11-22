import json
from datetime import datetime
from pathlib import Path

from .db import Database


def export_audit(target: Path) -> dict:
    database = Database()
    database.initialize()
    payload = {
        "format": "paicode-audit-1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sessions": [],
        "agent_runs": [],
        "contracts": [],
        "findings": [],
        "validation_runs": [],
    }
    with database.connection() as conn:
        payload["sessions"] = [
            dict(row)
            for row in conn.execute(
                "SELECT id, workspace, created_at, last_opened_at, title, stats_json FROM sessions ORDER BY created_at"
            ).fetchall()
        ]
        payload["agent_runs"] = [
            dict(row)
            for row in conn.execute(
                "SELECT id, session_id, agent_id, role, phase, status, model, total_tokens, summary, error, started_at, finished_at "
                "FROM agent_runs ORDER BY started_at"
            ).fetchall()
        ]
        payload["contracts"] = [
            dict(row)
            for row in conn.execute(
                "SELECT id, session_id, feature, contract_json, created_at FROM build_contracts ORDER BY created_at"
            ).fetchall()
        ]
        payload["findings"] = [
            dict(row)
            for row in conn.execute(
                "SELECT id, validation_id, session_id, owner, severity, title, file, line, expected, actual, command, fix, message, status, created_at "
                "FROM validation_findings ORDER BY created_at"
            ).fetchall()
        ]
        payload["validation_runs"] = [
            dict(row)
            for row in conn.execute(
                "SELECT id, session_id, contract_id, round_number, status, summary, findings_count, started_at, finished_at "
                "FROM validation_runs ORDER BY started_at"
            ).fetchall()
        ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "path": str(target),
        "sessions": len(payload["sessions"]),
        "agent_runs": len(payload["agent_runs"]),
        "contracts": len(payload["contracts"]),
        "findings": len(payload["findings"]),
        "validation_runs": len(payload["validation_runs"]),
    }
