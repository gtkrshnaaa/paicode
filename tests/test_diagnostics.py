import json
import sys
from pathlib import Path

from paicode.cli import main
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderStore
from paicode.tools.registry import ToolRegistry

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


def write_settings(project: Path, payload: dict) -> None:
    path = project / ".paicode" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_diagnostics_tool_runs_configured_commands(project: Path, config_home: Path):
    write_settings(
        project,
        {"diagnostics": [f"{sys.executable} -c \"print('clean')\""]},
    )
    registry = ToolRegistry(project, UsageStats(), [])
    result = registry.execute("diagnostics", {})
    assert result.ok is True
    assert "clean" in result.output
    names = {item["function"]["name"] for item in registry.schemas}
    assert "diagnostics" in names


def test_diagnostics_hidden_in_read_only_mode(project: Path, config_home: Path):
    write_settings(project, {"diagnostics": [f"{sys.executable} -c \"print('clean')\""]})
    registry = ToolRegistry(project, UsageStats(), [], read_only_shell=True, strict_read_only_shell=True)
    names = {item["function"]["name"] for item in registry.schemas}
    assert "diagnostics" not in names
    result = registry.execute("diagnostics", {})
    assert result.ok is False


def test_headless_json_events(project: Path, config_home: Path, capsys):
    def responder(index, payload):
        return [text_chunk("json answer"), finish_chunk("stop"), usage_chunk(5, 2, 7)]

    with FakeOpenAI(responder) as server:
        store = ProviderStore()
        store.upsert("fake", server.base_url, api_key="test-key", model="fake-model")
        store.set_active("fake")
        code = main(["--path", str(project), "run", "--single-agent", "--json", "hello"])
    output = capsys.readouterr().out
    rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    kinds = [row["type"] for row in rows]
    assert code == 0
    assert "TextDelta" in kinds
    assert "Finished" in kinds
    assert any(row.get("text") == "json answer" for row in rows)
