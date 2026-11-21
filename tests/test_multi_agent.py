import json
from pathlib import Path

from paicode.agents import MultiAgentRunner
from paicode.agents.store import AgentStore
from paicode.agent.events import AgentPhase, Finished, TextDelta
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig
from paicode.rules.loader import load_rules

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, tool_chunk, usage_chunk


def _proposal(agent: int) -> dict:
    return {
        "agent": agent,
        "role": "builder",
        "understanding": f"agent {agent} reviewed the math utility",
        "files": [],
        "interfaces": ["add(left, right)"],
        "tests": ["add(2, 3) == 5"],
        "risks": [],
        "objections": [],
        "owned_areas": ["math"],
    }


def _contract() -> dict:
    return {
        "feature": "Math utility",
        "acceptance": ["add returns the sum"],
        "work_units": [
            {
                "id": "wu-1",
                "title": "math module",
                "owner": 2,
                "files": ["math_ops.py"],
                "interfaces": "def add(left, right)",
                "notes": "Keep it small.",
            },
            {
                "id": "wu-2",
                "title": "unit tests",
                "owner": 3,
                "files": ["test_math.py"],
                "interfaces": "unittest test case",
                "notes": "Test add.",
            },
        ],
        "shared_files": [],
        "interfaces": "add(left: int, right: int) -> int",
        "api": "",
        "database": "",
        "ui": "",
        "test_plan": ["test_add verifies 2 + 3"],
        "commands": {"test": "python3 -m unittest -q"},
        "non_goals": [],
        "risks": [],
    }


def _finish(payload: dict):
    return tool_chunk("finish", "finish", json.dumps({"summary": json.dumps(payload)}))


def _builder_turns(system: str, payload: dict, agent: int):
    if any(message.get("role") == "tool" for message in payload["messages"]):
        return [_finish({"status": "done", "summary": "done", "files": [], "commands": [], "blockers": []})]
    if agent == 2:
        body = (
            "def add(left, right):\n    return left + right\n"
            if "Repair findings" in system
            else "def add(left, right):\n    return left - right\n"
        )
        return [
            tool_chunk("write-2", "write", json.dumps({"path": "math_ops.py", "content": body})),
            finish_chunk("tool_calls"),
            usage_chunk(10, 5, 15),
        ]
    return [
        tool_chunk(
            "write-3",
            "write",
            json.dumps(
                {
                    "path": "test_math.py",
                    "content": (
                        "import unittest\n"
                        "from math_ops import add\n\n"
                        "class MathTests(unittest.TestCase):\n"
                        "    def test_add(self):\n"
                        "        self.assertEqual(add(2, 3), 5)\n"
                    ),
                }
            ),
        ),
        finish_chunk("tool_calls"),
        usage_chunk(10, 5, 15),
    ]


def test_multi_agent_council_parallel_build_and_validator_repair(project: Path, config_home: Path):
    state = {"validator": 0}

    def responder(index, payload):
        messages = payload["messages"]
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        user = messages[-1]["content"] if messages else ""

        if "council proposal round" in user:
            agent = 2
            for number in range(2, 22):
                if f"agent {number}" in user:
                    agent = number
                    break
            return [text_chunk(json.dumps(_proposal(agent))), finish_chunk("stop"), usage_chunk(10, 5, 15)]
        if "Write the final report directly to the user" in user:
            return [
                text_chunk("## Summary\n\nLead report delivered.\n\n## Delivered\n\nTests passed."),
                finish_chunk("stop"),
                usage_chunk(5, 5, 10),
            ]
        if "Synthesize the council proposals" in user:
            return [text_chunk(json.dumps(_contract())), finish_chunk("stop"), usage_chunk(20, 10, 30)]
        if "Review this frozen-candidate contract" in user:
            return [
                text_chunk(json.dumps({"agent": 2, "verdict": "approve", "required_changes": [], "notes": "ok"})),
                finish_chunk("stop"),
                usage_chunk(10, 5, 15),
            ]
        if "independent Validator" in system:
            state["validator"] += 1
            if state["validator"] == 1:
                summary = {
                    "ok": False,
                    "summary": "add returns the difference.",
                    "commands": ["python3 -m unittest -q: failed"],
                    "findings": [
                        {
                            "owner": 2,
                            "severity": "critical",
                            "title": "add returns the difference",
                            "file": "math_ops.py",
                            "expected": "5",
                            "actual": "-1",
                            "command": "python3 -m unittest -q",
                            "fix": "return left + right",
                            "message": "Agent 2. Fix add now.",
                        }
                    ],
                }
            else:
                summary = {
                    "ok": True,
                    "summary": "All tests pass.",
                    "commands": ["python3 -m unittest -q: ok"],
                    "findings": [],
                }
            return [_finish(summary)]
        if "builder in a parallel team" in system:
            agent = 2 if "You are Paicode agent 2" in system else 3
            return _builder_turns(system, payload, agent)
        return [text_chunk("{}"), finish_chunk("stop"), usage_chunk(1, 1, 2)]

    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        marker = "GLOBAL-RULE-MARKER-7f3a9c"
        (config_home / "PAICODE.md").write_text(marker, encoding="utf-8")
        events = []
        stats = UsageStats()
        runner = MultiAgentRunner(
            project,
            provider,
            stats,
            rules=load_rules(project),
            skills=[],
            emit=events.append,
            session_id="multi-test",
            concurrency=22,
        )
        summary = runner.run("Build a math utility with add and tests.")
        assert summary
        assert runner.contract is not None
        assert len(runner.contract.work_units) == 2
        assert (project / "math_ops.py").read_text(encoding="utf-8").strip().endswith("return left + right")
        assert (project / "test_math.py").is_file()
        assert any(isinstance(event, AgentPhase) and event.phase == "council" for event in events)
        assert any(isinstance(event, AgentPhase) and event.phase == "build" for event in events)
        assert any(isinstance(event, AgentPhase) and event.phase == "validate" for event in events)
        assert any(isinstance(event, TextDelta) and "Lead report delivered" in event.text for event in events)
        assert isinstance(events[-1], Finished)
        assert server.requests
        for payload in server.requests:
            text = "\n".join(str(message.get("content", "")) for message in payload["messages"])
            assert marker in text
        store = AgentStore()
        assert store.strike_count("multi-test", 2) == 1
        statuses = {row["agent_id"]: row for row in store.agent_status("multi-test")}
        assert statuses[1]["status"] == "done"
        assert statuses[2]["status"] == "done"
        assert statuses[3]["status"] == "done"
        assert statuses[22]["status"] == "passed"
