import re
from pathlib import Path

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
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


def test_diff_divider_has_index_path_and_counts(project: Path, config_home: Path):
    pane = DiffPane()
    text = pane._divider("DIFF 03  src/app.py", "+12 -4  14:32")
    plain = text.plain
    assert "DIFF 03" in plain
    assert "src/app.py" in plain
    assert "+12 -4" in plain
    assert "14:32" in plain
    assert plain.count("─") > 20
