import json
from pathlib import Path

import threading

from paicode.agent.events import ErrorEvent, Finished, ToolFinished
from paicode.agent.loop import AgentRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, tool_chunk, usage_chunk


def responder(index, payload):
    if index == 0:
        return [
            tool_chunk("call_write", "write", json.dumps({"path": "hello.txt", "content": "LIVE"})),
            finish_chunk("tool_calls"),
            usage_chunk(20, 10, 30),
        ]
    return [
        tool_chunk("call_finish", "finish", json.dumps({"summary": "Created hello.txt"})),
        finish_chunk("tool_calls"),
        usage_chunk(30, 8, 38),
    ]


def test_agent_loop_executes_write_and_finish(project: Path):
    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        events = []
        stats = UsageStats()
        runner = AgentRunner(project, provider, stats, rules=[], skills=[], emit=events.append)
        runner.run("Create hello.txt with LIVE")
        assert (project / "hello.txt").read_text(encoding="utf-8") == "LIVE"
        assert stats.files_created == 1
        assert stats.total_tokens == 68
        assert any(isinstance(event, ToolFinished) and event.name == "write" and event.ok for event in events)
        assert isinstance(events[-1], Finished)
        assert not (project / ".pai_brain").exists()
        assert not (project / ".pai_history").exists()


def test_agent_runner_honors_external_stop_event(project: Path):
    with FakeOpenAI(lambda index, payload: []) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        stop = threading.Event()
        stop.set()
        events = []
        runner = AgentRunner(
            project,
            provider,
            UsageStats(),
            rules=[],
            skills=[],
            emit=events.append,
            stop_event=stop,
        )
        runner.run("Do not run.")
        assert any(isinstance(event, ErrorEvent) and "Stopped" in event.message for event in events)
        assert not server.requests
