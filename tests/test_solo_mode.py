import json
from pathlib import Path

from paicode.agent.events import AgentPhase, Finished, TextDelta
from paicode.agents.solo import SoloRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig
from paicode.tools.registry import ToolRegistry

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


def provider(server) -> ProviderConfig:
    return ProviderConfig(
        name="fake",
        base_url=server.base_url,
        api_keys=["test-key"],
        model="fake-model",
    )


def test_solo_runner_plans_then_acts(project: Path, config_home: Path):
    plan = {
        "read_only": False,
        "goal": "Add a greeting",
        "steps": ["Inspect README.md", "Edit README.md", "Verify"],
        "files": ["README.md"],
        "risks": [],
    }

    def responder(index, payload):
        if index == 0:
            return [text_chunk(json.dumps(plan)), finish_chunk("stop"), usage_chunk(100, 20, 120, 80, 20)]
        return [text_chunk("implemented"), finish_chunk("stop"), usage_chunk(200, 30, 230, 180, 20)]

    with FakeOpenAI(responder) as server:
        events = []
        stats = UsageStats()
        runner = SoloRunner(project, provider(server), stats, [], [], events.append)
        text = runner.run("Add a greeting to the README.")
        assert text == "implemented"
        assert runner.plan["goal"] == "Add a greeting"
        assert any(isinstance(event, AgentPhase) and event.phase == "plan" for event in events)
        assert any(isinstance(event, TextDelta) and "Solo plan" in event.text for event in events)
        assert sum(isinstance(event, Finished) for event in events) == 1
        assert stats.requests == 2
        assert stats.cache_hit_tokens == 260
        assert stats.cache_miss_tokens == 40
        assert "APPROVED PLAN" in server.requests[1]["messages"][0]["content"]
        assert server.requests[0]["max_tokens"] == 1200
        assert server.requests[1]["max_tokens"] == 8192


def test_solo_runner_read_only_plan_uses_discussion(project: Path, config_home: Path):
    plan = {
        "read_only": True,
        "goal": "Explain the project",
        "steps": ["Read README.md"],
        "files": [],
        "risks": [],
    }

    def responder(index, payload):
        if index == 0:
            return [text_chunk(json.dumps(plan)), finish_chunk("stop"), usage_chunk(50, 10, 60)]
        return [text_chunk("analysis"), finish_chunk("stop"), usage_chunk(60, 10, 70)]

    with FakeOpenAI(responder) as server:
        runner = SoloRunner(project, provider(server), UsageStats(), [], [], lambda event: None)
        text = runner.run("Explain the project.")
        assert text == "analysis"
        tools = server.requests[1].get("tools", [])
        names = {item["function"]["name"] for item in tools}
        assert "write" not in names
        assert "edit" not in names
        assert "todo" in names


def test_solo_step_cap_defaults_when_zero(project: Path, config_home: Path):
    runner = SoloRunner(
        project,
        ProviderConfig(name="fake", base_url="http://127.0.0.1:9/v1", api_keys=["x"], model="fake"),
        UsageStats(),
        [],
        [],
        lambda event: None,
        max_steps=0,
    )
    assert runner.max_steps == 60


def test_todo_tool_tracks_checklist(project: Path, config_home: Path):
    registry = ToolRegistry(project, UsageStats(), [])
    result = registry.execute(
        "todo",
        {
            "items": [
                {"title": "Inspect files", "status": "done"},
                {"title": "Apply edit", "status": "in_progress"},
            ]
        },
    )
    assert result.ok is True
    assert "[x] Inspect files" in result.output
    assert "[>] Apply edit" in result.output
    assert registry.todos[1]["title"] == "Apply edit"


def test_headless_default_uses_solo(project: Path, config_home: Path, capsys):
    plan = {"read_only": False, "goal": "Say hello", "steps": ["Answer"], "files": [], "risks": []}

    def responder(index, payload):
        if index == 0:
            return [text_chunk(json.dumps(plan)), finish_chunk("stop"), usage_chunk(20, 5, 25)]
        return [text_chunk("hello"), finish_chunk("stop"), usage_chunk(30, 5, 35)]

    from paicode.cli import main
    from paicode.providers.store import ProviderStore

    with FakeOpenAI(responder) as server:
        store = ProviderStore()
        store.upsert("fake", server.base_url, api_key="test-key", model="fake-model")
        store.set_active("fake")
        code = main(["--path", str(project), "run", "--json", "Say hello."])
    output = capsys.readouterr().out
    rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    kinds = [row["type"] for row in rows]
    assert code == 0
    assert "AgentPhase" in kinds
    assert any(row.get("phase") == "plan" for row in rows if row["type"] == "AgentPhase")
    assert any(row.get("text") == "hello" for row in rows if row["type"] == "TextDelta")
