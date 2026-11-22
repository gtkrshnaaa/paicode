import json
from pathlib import Path

import pytest

from paicode.agent.events import AgentAction, TextDelta
from paicode.agents.smart import SmartRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig
from paicode.rules.loader import load_rules

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


class StubInner:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.stopped = False

    def run(self, text, images=None):
        return f"inner:{text}"

    def request_stop(self):
        self.stopped = True

    def agent_status(self):
        return []

    def latest_findings(self):
        return []


def _triage_responder(decision: dict):
    def responder(index, payload):
        return [text_chunk(json.dumps(decision)), finish_chunk("stop"), usage_chunk(10, 5, 15)]

    return responder


@pytest.mark.parametrize(
    "decision, expected_kind",
    [
        ({"intent": "analysis", "mode": "single", "expected_files": 0}, "discussion"),
        ({"intent": "write", "mode": "single", "expected_files": 1}, "agent"),
        ({"intent": "write", "mode": "single", "expected_files": 3}, "multi"),
        ({"intent": "write", "mode": "single", "expected_files": 0}, "multi"),
        ({"intent": "scaffold", "mode": "single", "expected_files": 1}, "multi"),
    ],
)
def test_smart_runner_routing(
    project: Path, config_home: Path, monkeypatch, decision, expected_kind
):
    captured = {}

    class StubDiscussion(StubInner):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["inner"] = "discussion"

    class StubAgent(StubInner):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["inner"] = "agent"

    class StubMulti(StubInner):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["inner"] = "multi"

    monkeypatch.setattr("paicode.agents.smart.DiscussionRunner", StubDiscussion)
    monkeypatch.setattr("paicode.agents.smart.AgentRunner", StubAgent)
    monkeypatch.setattr("paicode.agents.smart.MultiAgentRunner", StubMulti)
    (config_home / "PAICODE.md").write_text("SMART-RULE-MARKER", encoding="utf-8")

    with FakeOpenAI(_triage_responder(decision)) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        events = []
        runner = SmartRunner(
            project,
            provider,
            UsageStats(),
            load_rules(project),
            [],
            emit=events.append,
            session_id="smart-test",
        )
        result = runner.run("do the thing")
        assert result == "inner:do the thing"
        assert captured["inner"] == expected_kind
        assert any(isinstance(event, AgentAction) and event.kind == "route" for event in events)
        assert any(isinstance(event, TextDelta) and "Lead triage" in event.text for event in events)
        assert server.requests
        text = "\n".join(str(message.get("content", "")) for message in server.requests[0]["messages"])
        assert "SMART-RULE-MARKER" in text
