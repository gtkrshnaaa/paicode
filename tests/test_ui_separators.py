import re
from pathlib import Path

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from textual.widgets import Markdown

from paicode.tui.widgets.diff import DiffPane


async def test_chat_turn_dividers_between_turns(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        app.chat.add_user("first turn")
        app.chat.add_assistant("first answer")
        app.chat.add_user("second turn")
        app.chat.add_assistant("second answer")
        await pilot.pause()
        dividers = [child for child in app.chat._scroll().children if "turn-divider" in child.classes]
        assert len(dividers) == 1
        text = app.chat._turn_divider()
        plain = text.plain
        assert "TURN 02" in plain
        assert re.search(r"\b\d{2}:\d{2}\b", plain)


async def test_chat_restore_rebuilds_turn_dividers(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        app.chat.restore(
            [
                {"kind": "user", "text": "one"},
                {"kind": "assistant", "text": "answer one"},
                {"kind": "user", "text": "two"},
                {"kind": "assistant", "text": "answer two"},
            ]
        )
        await pilot.pause()
        dividers = [child for child in app.chat._scroll().children if "turn-divider" in child.classes]
        assert len(dividers) == 1


async def test_chat_keeps_text_tools_and_report_in_order(
    project: Path, config_home: Path
):
    from textual.containers import Vertical

    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        app.chat.begin_assistant()
        app.chat.append_assistant("Before tool")
        app.chat.add_tool("bash", "ok", "pytest -q")
        app.chat.append_assistant("Final report")
        await pilot.pause(0.2)
        kinds = []
        labels = []
        sources = []
        for child in app.chat._scroll().children:
            if isinstance(child, Vertical) and "assistant-card" in child.classes:
                kinds.append("assistant")
                labels.append(child.query_one(".role").content.plain)
                sources.append(child.query_one(Markdown).source)
            elif "tool" in child.classes:
                kinds.append("tool")
        assert kinds == ["assistant", "tool", "assistant"]
        assert labels[0].startswith("PAI")
        assert labels[1].startswith("PAI")
        assert re.search(r"\b\d{2}:\d{2}\b", labels[1])
        assert "Before tool" in sources[0]
        assert "Final report" in sources[1]


def test_diff_divider_has_index_path_and_counts(project: Path, config_home: Path):
    pane = DiffPane()
    text = pane._divider("DIFF 03  src/app.py", "+12 -4  14:32")
    plain = text.plain
    assert "DIFF 03" in plain
    assert "src/app.py" in plain
    assert "+12 -4" in plain
    assert "14:32" in plain
    assert plain.count("─") > 20
