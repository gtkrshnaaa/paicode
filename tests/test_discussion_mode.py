import json
from pathlib import Path

from paicode.agent.events import ToolFinished
from paicode.agents import DiscussionRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig
from paicode.rules.loader import load_rules

from .fake_openai import FakeOpenAI, finish_chunk, tool_chunk, usage_chunk


def test_discussion_mode_blocks_file_writes(project: Path, config_home: Path):
    marker = "DISCUSSION-RULE-MARKER"
    (config_home / "PAICODE.md").write_text(marker, encoding="utf-8")

    def responder(index, payload):
        if index == 0:
            return [
                tool_chunk("write", "write", json.dumps({"path": "pwned.txt", "content": "no"})),
                finish_chunk("tool_calls"),
                usage_chunk(10, 5, 15),
            ]
        return [
            tool_chunk("finish", "finish", json.dumps({"summary": "discussion complete"})),
            finish_chunk("tool_calls"),
            usage_chunk(10, 5, 15),
        ]

    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        events = []
        runner = DiscussionRunner(
            project,
            provider,
            UsageStats(),
            load_rules(project),
            [],
            emit=events.append,
        )
        summary = runner.run("Discuss the architecture. Do not code.")
        assert summary == "discussion complete"
        assert not (project / "pwned.txt").exists()
        assert any(isinstance(event, ToolFinished) and event.name == "write" and not event.ok for event in events)
        assert server.requests
        for payload in server.requests:
            text = "\n".join(str(message.get("content", "")) for message in payload["messages"])
            assert marker in text


async def test_disscus_command_uses_discussion_runner(
    project: Path, config_home: Path, monkeypatch
):
    captured = {}

    class StubRunner:
        def __init__(self, *args, **kwargs):
            captured["runner"] = self

        def request_stop(self):
            return None

    monkeypatch.setattr("paicode.tui.app.DiscussionRunner", StubRunner)
    from paicode.providers.store import ProviderStore
    from paicode.tui.app import PaiCodeApp

    app = PaiCodeApp(project, ProviderStore())
    app.store.upsert("fake", "http://127.0.0.1:9/v1", api_key="test", model="fake")
    app.store.set_active("fake")
    app._run_agent = lambda runner, text, images: captured.setdefault("run", (runner, text))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._cmd_disscus("compare two designs")
        await pilot.pause()
        assert isinstance(captured["runner"], StubRunner)
        assert captured["run"][1] == "compare two designs"
        assert app._active_mode == "discussion"
        app.busy = False


async def test_discuss_alias(
    project: Path, config_home: Path, monkeypatch
):
    captured = {}

    class StubRunner:
        def __init__(self, *args, **kwargs):
            captured["runner"] = self

        def request_stop(self):
            return None

    monkeypatch.setattr("paicode.tui.app.DiscussionRunner", StubRunner)
    from paicode.providers.store import ProviderStore
    from paicode.tui.app import PaiCodeApp

    app = PaiCodeApp(project, ProviderStore())
    app.store.upsert("fake", "http://127.0.0.1:9/v1", api_key="test", model="fake")
    app.store.set_active("fake")
    app._run_agent = lambda runner, text, images: captured.setdefault("run", (runner, text))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._cmd_discuss("alias works")
        await pilot.pause()
        assert isinstance(captured["runner"], StubRunner)
        app.busy = False


def test_discussion_mode_blocks_shell_writes(project: Path, config_home: Path):
    def responder(index, payload):
        if index == 0:
            return [
                tool_chunk("bash", "bash", json.dumps({"command": "echo pwned > shell-pwned.txt"})),
                finish_chunk("tool_calls"),
                usage_chunk(10, 5, 15),
            ]
        return [
            tool_chunk("finish", "finish", json.dumps({"summary": "discussion complete"})),
            finish_chunk("tool_calls"),
            usage_chunk(10, 5, 15),
        ]

    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        events = []
        runner = DiscussionRunner(
            project,
            provider,
            UsageStats(),
            [],
            [],
            emit=events.append,
        )
        runner.run("Discuss only.")
        assert not (project / "shell-pwned.txt").exists()
        assert any(
            isinstance(event, ToolFinished)
            and event.name == "bash"
            and not event.ok
            for event in events
        )
