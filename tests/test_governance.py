import json
from pathlib import Path

from paicode.agent.events import ErrorEvent, Finished
from paicode.agent.loop import AgentRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig
from paicode.security import set_approval_handler
from paicode.telemetry import Telemetry
from paicode.tools.registry import ToolRegistry

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


def write_settings(project: Path, payload: dict) -> None:
    path = project / ".paicode" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def responder(index, payload):
    return [text_chunk("ok"), finish_chunk("stop"), usage_chunk(10, 2, 12)]


def provider(server) -> ProviderConfig:
    return ProviderConfig(
        name="fake",
        base_url=server.base_url,
        api_keys=["test-key"],
        model="fake-model",
    )


def test_deny_rule_blocks_shell(project: Path, config_home: Path):
    write_settings(
        project,
        {"permissions": [{"action": "shell", "resource": "*", "effect": "deny"}]},
    )
    registry = ToolRegistry(project, UsageStats(), [])
    result = registry.execute("bash", {"command": "echo ok"})
    assert result.ok is False
    assert "Denied by permission policy" in result.output


def test_strict_mode_requires_approval(project: Path, config_home: Path):
    write_settings(project, {"permission_mode": "strict"})
    registry = ToolRegistry(project, UsageStats(), [])
    blocked = registry.execute("write", {"path": "strict.txt", "content": "x"})
    assert blocked.ok is False
    assert "Approval required" in blocked.output

    set_approval_handler(lambda action, resource: True)
    try:
        allowed = registry.execute("write", {"path": "strict.txt", "content": "x"})
    finally:
        set_approval_handler(None)
    assert allowed.ok is True
    assert (project / "strict.txt").read_text(encoding="utf-8") == "x"


def test_budget_stops_the_run(project: Path, config_home: Path):
    write_settings(project, {"budget": {"max_tokens": 5}})
    with FakeOpenAI(responder) as server:
        events = []
        runner = AgentRunner(project, provider(server), UsageStats(), [], [], events.append)
        runner.run("Do the thing.")
        errors = [event for event in events if isinstance(event, ErrorEvent)]
        assert errors
        assert "Token budget exceeded" in errors[-1].message
        assert not any(isinstance(event, Finished) for event in events)


def test_telemetry_writes_jsonl(project: Path, config_home: Path):
    write_settings(project, {"telemetry": True})
    with FakeOpenAI(responder) as server:
        runner = AgentRunner(project, provider(server), UsageStats(), [], [], lambda event: None)
        runner.run("Write telemetry.")
    path = Telemetry(project).path
    assert path.is_file()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    kinds = [row["kind"] for row in rows]
    assert "run_start" in kinds
    assert "run_end" in kinds
    assert all("Write telemetry" not in json.dumps(row) for row in rows)
