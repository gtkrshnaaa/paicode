from pathlib import Path

from paicode.agent.events import AgentStatus
from paicode.cli import _build_parser, main
from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp


def test_single_agent_flag_parser():
    parser = _build_parser()
    assert parser.parse_args(["run", "--single-agent", "hello"]).single_agent is True
    assert parser.parse_args(["run", "hello"]).single_agent is False
    assert parser.parse_args(["--single-agent"]).single_agent is True
    assert parser.parse_args(["run", "--team", "hello"]).team is True
    assert parser.parse_args(["run", "hello"]).team is False
    assert parser.parse_args(["--team"]).team is True


def test_tui_defaults_to_solo_mode(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    assert app.multi_agent is False


def test_tui_team_override(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore(), multi_agent=True)
    assert app.multi_agent is True


async def test_tui_start_prompt_uses_solo_runner(
    project: Path, config_home: Path, monkeypatch
):
    captured = {}

    class StubRunner:
        def __init__(self, *args, **kwargs):
            captured["runner"] = self
            captured["kwargs"] = kwargs

        def request_stop(self):
            return None

    monkeypatch.setattr("paicode.tui.app.SoloRunner", StubRunner)
    app = PaiCodeApp(project, ProviderStore())
    app.store.upsert("fake", "http://127.0.0.1:9/v1", api_key="test", model="fake")
    app.store.set_active("fake")
    app._run_agent = lambda runner, text, images: captured.setdefault("run", (runner, text, images))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._start_prompt("build it", [], "build it")
        await pilot.pause()
        assert isinstance(captured["runner"], StubRunner)
        assert captured["kwargs"]["session_id"] == app.session.record.id
        assert captured["kwargs"]["history"] == app.session.messages
        assert captured["run"][1] == "build it"
        app.busy = False


async def test_team_command_uses_multi_agent_runner(
    project: Path, config_home: Path, monkeypatch
):
    captured = {}

    class StubRunner:
        def __init__(self, *args, **kwargs):
            captured["runner"] = self
            captured["kwargs"] = kwargs

        def request_stop(self):
            return None

    monkeypatch.setattr("paicode.tui.app.MultiAgentRunner", StubRunner)
    app = PaiCodeApp(project, ProviderStore())
    app.store.upsert("fake", "http://127.0.0.1:9/v1", api_key="test", model="fake")
    app.store.set_active("fake")
    app._run_agent = lambda runner, text, images: captured.setdefault("run", (runner, text, images))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._start_prompt("build it", [], "build it", mode="team")
        await pilot.pause()
        assert isinstance(captured["runner"], StubRunner)
        assert captured["kwargs"]["session_id"] == app.session.record.id
        app.busy = False


async def test_agents_command_lists_council(
    project: Path, config_home: Path, monkeypatch
):
    from paicode.agents import MultiAgentRunner

    app = PaiCodeApp(project, ProviderStore())
    app.store.upsert("fake", "http://127.0.0.1:9/v1", api_key="test", model="fake")
    app.store.set_active("fake")
    provider = app.store.active()
    runner = MultiAgentRunner(
        project, provider, app.stats, [], [], emit=lambda event: None,
        session_id="agents-test",
    )
    runner.agent_status = lambda: [
        {"agent_id": 1, "role": "Lead Architect", "phase": "council", "status": "done", "total_tokens": 10},
        {"agent_id": 2, "role": "Builder", "phase": "build", "status": "done", "total_tokens": 20},
    ]
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._active_runner = runner
        app._cmd_agents("")
        await pilot.pause()
        text = " ".join(str(entry.get("text", "")) for entry in app.chat.transcript)
        assert "Agent 1 Lead Architect" in text
        assert "Agent 2 Builder" in text


async def test_review_objections_do_not_spam_chat(
    project: Path, config_home: Path
):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        before = len(app.chat.transcript)
        app._handle_event(
            AgentStatus(19, "Data and Fixtures", "council-review", "object", "needs schema")
        )
        await pilot.pause()
        assert len(app.chat.transcript) == before

        app._handle_event(AgentStatus(19, "Data and Fixtures", "build", "failed", "boom"))
        await pilot.pause()
        assert len(app.chat.transcript) == before + 1
        assert "failed: boom" in app.chat.transcript[-1]["text"]


def test_doctor_reports_multi_agent(config_home: Path, capsys):
    code = main(["doctor"])
    output = capsys.readouterr().out
    assert code == 0
    assert "Agents: solo default" in output
