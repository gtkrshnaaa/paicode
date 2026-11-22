import json
from pathlib import Path

from paicode.audit_export import export_audit
from paicode.cli import main
from paicode.sessions import SessionStore


def test_audit_export_contains_session_data(project: Path, config_home: Path):
    store = SessionStore()
    data = store.create(project, "audit session")
    data.transcript.append({"kind": "user", "text": "hello"})
    store.save(data)
    target = project / "audit.json"
    result = export_audit(target)
    assert result["sessions"] == 1
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["format"] == "paicode-audit-1"
    assert payload["sessions"][0]["title"] == "audit session"
    assert "api_key" not in target.read_text(encoding="utf-8").lower()


def test_audit_cli_writes_file(project: Path, config_home: Path):
    target = project / "audit-cli.json"
    assert main(["--path", str(project), "audit", "--out", str(target)]) == 0
    assert target.is_file()
