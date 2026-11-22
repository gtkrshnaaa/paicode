from pathlib import Path

from paicode.agent.events import AgentAction
from paicode.agents.actions import tool_kind
from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets.agent_rail import AgentRail


def test_tool_kind_mapping():
    assert tool_kind("read") == "read"
    assert tool_kind("write") == "create"
    assert tool_kind("bash") == "command"
    assert tool_kind("grep") == "search"
    assert tool_kind("skill") == "skill"


async def test_agent_rail_tracks_nested_turns(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(180, 52)) as pilot:
        await pilot.pause()
        rail = app.query_one(AgentRail)
        assert len(rail._cards) == 22
        rail.set_phase("build", "8 builders")
        rail.set_status(2, "Frontend Shell", "running", "writing index.html")
        rail.add_action(2, "Frontend Shell", "create", "index.html", "done")
        rail.add_action(2, "Frontend Shell", "command", "node --test", "done")
        rail.add_action(2, "Frontend Shell", "edit", "quotes.html", "running")
        card = rail._cards[2]
        assert len(card.turns) == 4
        assert card.turns[0]["kind"] == "status"
        assert card.turns[1]["kind"] == "create"
        assert card.turns[3]["kind"] == "edit"
        assert "AGENTS" in rail._title.content.plain
        assert "build" in rail._title.content.plain

        app._handle_event(
            AgentAction(3, "UI Components", "read", "components/button.css", "done", "06:42")
        )
        await pilot.pause()
        assert rail._cards[3].turns[0]["kind"] == "read"
