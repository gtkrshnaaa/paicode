import json
import threading
from pathlib import Path

from paicode.agent.events import AgentPhase, TextDelta
from paicode.agents import MultiAgentRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, tool_chunk, usage_chunk


def _finish(payload: dict):
    return tool_chunk("finish", "finish", json.dumps({"summary": json.dumps(payload)}))


def test_eight_builders_start_together_and_validator_waits(
    project: Path, config_home: Path
):
    owners = list(range(2, 10))
    barrier = threading.Barrier(len(owners), timeout=10)
    lock = threading.Lock()
    state = {"finished": 0, "validator_after_all": False}
    contract = {
        "feature": "Eight files",
        "acceptance": ["all files exist"],
        "work_units": [
            {
                "id": f"wu-{owner}",
                "title": f"file {owner}",
                "owner": owner,
                "files": [f"file{owner}.txt"],
                "interfaces": "",
                "notes": "",
            }
            for owner in owners
        ],
        "shared_files": [],
        "interfaces": "",
        "api": "",
        "database": "",
        "ui": "",
        "test_plan": ["all files exist"],
        "commands": {"test": " && ".join(f"test -f file{owner}.txt" for owner in owners)},
        "non_goals": [],
        "risks": [],
    }

    def responder(index, payload):
        messages = payload["messages"]
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        user = messages[-1]["content"] if messages else ""
        if "council proposal round" in user:
            return [text_chunk(json.dumps({"agent": 2, "understanding": "ok"})), finish_chunk("stop"), usage_chunk(1, 1, 2)]
        if "Synthesize the council proposals" in user:
            return [text_chunk(json.dumps(contract)), finish_chunk("stop"), usage_chunk(1, 1, 2)]
        if "Review this frozen-candidate contract" in user:
            return [text_chunk(json.dumps({"agent": 2, "verdict": "approve"})), finish_chunk("stop"), usage_chunk(1, 1, 2)]
        if "independent Validator" in system:
            with lock:
                state["validator_after_all"] = state["finished"] == len(owners)
            return [_finish({"ok": True, "summary": "all files exist", "findings": [], "commands": []})]
        if "builder in a parallel team" in system:
            owner = 2
            for number in owners:
                if f"You are Paicode agent {number}" in system:
                    owner = number
                    break
            if any(message.get("role") == "tool" for message in messages):
                with lock:
                    state["finished"] += 1
                return [_finish({"status": "done", "summary": "done", "files": [f"file{owner}.txt"], "commands": [], "blockers": []})]
            barrier.wait()
            return [
                tool_chunk(
                    f"write-{owner}",
                    "write",
                    json.dumps({"path": f"file{owner}.txt", "content": f"agent {owner}\n"}),
                ),
                finish_chunk("tool_calls"),
                usage_chunk(1, 1, 2),
            ]
        if "Write the final report directly to the user" in user:
            return [text_chunk("## Summary\n\nEight builders completed in parallel."), finish_chunk("stop"), usage_chunk(1, 1, 2)]
        return [text_chunk(""), finish_chunk("stop"), usage_chunk(1, 1, 2)]

    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        events = []
        runner = MultiAgentRunner(
            project,
            provider,
            UsageStats(),
            rules=[],
            skills=[],
            emit=events.append,
            session_id="parallel-eight",
            concurrency=22,
        )
        runner.run("Create eight files in parallel.")
        assert barrier.n_waiting == 0
        assert state["validator_after_all"] is True
        for owner in owners:
            assert (project / f"file{owner}.txt").is_file()
        phases = [event for event in events if isinstance(event, AgentPhase) and event.phase == "build"]
        assert any(event.detail == "8 builders writing together" and event.active == 8 for event in phases)
        text = " ".join(event.text for event in events if isinstance(event, TextDelta))
        assert "started together" in text
        assert "all 8 builders finished" in text
