import json
from pathlib import Path

from paicode.agent.events import Finished, ToolFinished
from paicode.agent.loop import AgentRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, tool_chunk, usage_chunk


def responder(index, payload):
    module = (
        "def add(left, right):\n"
        "    return left - right\n"
    )
    fixed = (
        "def add(left, right):\n"
        "    return left + right\n"
    )
    tests = (
        "import unittest\n"
        "from calculator import add\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
    )
    calls = [
        ("write", {"path": "calculator.py", "content": module}),
        ("write", {"path": "test_calculator.py", "content": tests}),
        ("bash", {"command": "python3 -m unittest -q", "timeout": 30}),
        ("edit", {"path": "calculator.py", "old_string": "left - right", "new_string": "left + right"}),
        ("bash", {"command": "python3 -m unittest -q", "timeout": 30}),
        ("finish", {"summary": "Fixed add and verified the tests."}),
    ]
    if index >= len(calls):
        return [finish_chunk("stop")]
    name, arguments = calls[index]
    return [
        tool_chunk(f"call_{index}", name, json.dumps(arguments)),
        finish_chunk("tool_calls"),
        usage_chunk(20 + index, 5, 25 + index),
    ]


def test_agent_writes_tests_reads_failure_fixes_and_finishes(project: Path):
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
        runner.run("Fix the calculator and prove it with tests.")

        assert "return left + right" in (project / "calculator.py").read_text(encoding="utf-8")
        assert (project / "test_calculator.py").is_file()
        assert stats.commands == 2
        assert stats.files_created == 2
        assert stats.files_edited == 1

        commands = [
            event
            for event in events
            if isinstance(event, ToolFinished) and event.name == "bash"
        ]
        assert len(commands) == 2
        assert commands[0].ok is False
        assert commands[1].ok is True
        assert "FAILED" in commands[0].output or "Error" in commands[0].output
        assert isinstance(events[-1], Finished)
        assert len(server.requests) == 6
        assert not (project / ".pai_brain").exists()
        assert not (project / ".pai_history").exists()
