import json
import threading
from pathlib import Path

from paicode.agents import MultiAgentRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, tool_chunk, usage_chunk


def _finish(payload: dict):
    return tool_chunk("finish", "finish", json.dumps({"summary": json.dumps(payload)}))


def test_active_builders_start_together(project: Path, config_home: Path):
    barrier = threading.Barrier(2, timeout=8)
    contract = {
        "feature": "Two files",
        "acceptance": ["both files exist"],
        "work_units": [
            {"id": "a", "title": "a", "owner": 2, "files": ["a.txt"], "interfaces": "", "notes": ""},
            {"id": "b", "title": "b", "owner": 3, "files": ["b.txt"], "interfaces": "", "notes": ""},
        ],
        "shared_files": [],
        "interfaces": "",
        "api": "",
        "database": "",
        "ui": "",
        "test_plan": ["both files exist"],
        "commands": {"test": "test -f a.txt && test -f b.txt"},
        "non_goals": [],
        "risks": [],
    }

    def responder(index, payload):
        messages = payload["messages"]
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        user = messages[-1]["content"] if messages else ""
        if "council proposal round" in user:
            return [
                text_chunk(json.dumps({"agent": 2, "understanding": "ok"})),
                finish_chunk("stop"),
                usage_chunk(1, 1, 2),
            ]
        if "Synthesize the council proposals" in user:
            return [text_chunk(json.dumps(contract)), finish_chunk("stop"), usage_chunk(1, 1, 2)]
        if "Review this frozen-candidate contract" in user:
            return [
                text_chunk(json.dumps({"agent": 2, "verdict": "approve"})),
                finish_chunk("stop"),
                usage_chunk(1, 1, 2),
            ]
        if "independent Validator" in system:
            return [_finish({"ok": True, "summary": "ok", "findings": [], "commands": []})]
        if "in a parallel team" in system:
            if any(message.get("role") == "tool" for message in messages):
                return [_finish({"status": "done", "summary": "done", "files": [], "commands": [], "blockers": []})]
            barrier.wait()
            agent = 2 if "You are Paicode agent 2" in system else 3
            name = "a.txt" if agent == 2 else "b.txt"
            return [
                tool_chunk(
                    f"write-{agent}",
                    "write",
                    json.dumps({"path": name, "content": f"agent {agent}\n"}),
                ),
                finish_chunk("tool_calls"),
                usage_chunk(1, 1, 2),
            ]
        return [text_chunk(""), finish_chunk("stop"), usage_chunk(1, 1, 2)]

    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        runner = MultiAgentRunner(
            project,
            provider,
            UsageStats(),
            rules=[],
            skills=[],
            emit=lambda event: None,
            session_id="barrier-test",
            concurrency=22,
        )
        runner.run("Create two files.")
        assert (project / "a.txt").is_file()
        assert (project / "b.txt").is_file()
        assert barrier.n_waiting == 0
