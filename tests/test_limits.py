import json
from pathlib import Path

from paicode.agent.events import ErrorEvent, Finished, ToolFinished
from paicode.agent.loop import AgentRunner, compact_messages, context_budget
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, tool_chunk, usage_chunk


def _provider(server) -> ProviderConfig:
    return ProviderConfig(
        name="fake",
        base_url=server.base_url,
        api_keys=["test-key"],
        model="fake-model",
    )


def test_run_beyond_twelve_turns_when_unlimited(project: Path):
    (project / "big.txt").write_text("\n".join(f"line {number}" for number in range(1, 30)), encoding="utf-8")

    def responder(index, payload):
        if index < 15:
            return [
                tool_chunk(
                    f"call_{index}",
                    "read",
                    json.dumps({"path": "big.txt", "offset": index + 1, "limit": 1}),
                ),
                finish_chunk("tool_calls"),
                usage_chunk(10, 1, 11),
            ]
        return [
            tool_chunk("call_finish", "finish", json.dumps({"summary": "read all lines"})),
            finish_chunk("tool_calls"),
            usage_chunk(10, 1, 11),
        ]

    with FakeOpenAI(responder) as server:
        stats = UsageStats()
        events = []
        runner = AgentRunner(project, _provider(server), stats, [], [], events.append, max_steps=0)
        runner.run("Read one line at a time and finish.")
        assert not any(isinstance(event, ErrorEvent) for event in events)
        assert isinstance(events[-1], Finished)
        assert events[-1].steps == 16
        assert stats.files_read == 15
        assert len(server.requests) == 16


def test_repeated_identical_tool_call_stops_the_loop(project: Path):
    (project / "big.txt").write_text("one line\n", encoding="utf-8")

    def responder(index, payload):
        return [
            tool_chunk(
                f"call_{index}",
                "read",
                json.dumps({"path": "big.txt", "offset": 1, "limit": 1}),
            ),
            finish_chunk("tool_calls"),
            usage_chunk(10, 1, 11),
        ]

    with FakeOpenAI(responder) as server:
        events = []
        runner = AgentRunner(project, _provider(server), UsageStats(), [], [], events.append, max_steps=0)
        runner.run("Read the same line forever.")
        errors = [event for event in events if isinstance(event, ErrorEvent)]
        assert errors
        assert "Repeated identical tool call" in errors[-1].message
        assert not any(isinstance(event, Finished) for event in events)
        assert len([event for event in events if isinstance(event, ToolFinished)]) == 4
        assert len(server.requests) == 5


def test_compact_messages_keeps_large_tool_output():
    messages = [
        {"role": "system", "content": "system"},
        {"role": "tool", "content": "x" * 150_000, "tool_call_id": "call_1"},
        {"role": "user", "content": "continue"},
    ]
    compacted = compact_messages(messages, max_chars=2_500_000)
    assert len(compacted[1]["content"]) == 150_000


def test_compact_messages_drops_old_groups_when_over_budget():
    messages = [
        {"role": "system", "content": "system"},
        {"role": "tool", "content": "x" * 300_000, "tool_call_id": "call_1"},
        {"role": "user", "content": "continue"},
    ]
    compacted = compact_messages(messages, max_chars=10_000, keep_last=0)
    assert [message["role"] for message in compacted] == ["system", "user"]
    assert all(message["role"] != "tool" for message in compacted)


def test_context_budget_environment_override(monkeypatch):
    monkeypatch.setenv("PAICODE_CONTEXT_CHARS", "123456")
    assert context_budget() == 123456
