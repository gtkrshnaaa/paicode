from pathlib import Path

import pytest
from textual import events
from textual._xterm_parser import XTermParser

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets.prompt import PromptInput


def sequence_to_key(sequence: str) -> events.Key:
    parsed = list(XTermParser().feed(sequence))
    assert len(parsed) == 1
    return parsed[0]


async def test_shift_enter_inserts_newline_at_cursor(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await pilot.press("a", "b", "c")
        await pilot.press("shift+enter")
        await pilot.pause()
        assert prompt.text == "abc\n"
        await pilot.press("d")
        await pilot.pause()
        assert prompt.text == "abc\nd"


async def test_shift_enter_replaces_selection(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "abcdef"
        prompt.move_cursor((0, 3), select=True)
        await pilot.press("shift+enter")
        await pilot.pause()
        assert prompt.text == "\ndef"
        assert prompt.cursor_location == (1, 0)


@pytest.mark.parametrize(
    "sequence",
    [
        "\x1b[13;2u",
        "\x1b[27;2;13~",
        "\n",
    ],
)
async def test_terminal_newline_sequences(
    project: Path, config_home: Path, sequence: str
):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "abc"
        prompt.move_cursor((0, 3))
        await prompt._on_key(sequence_to_key(sequence))
        await pilot.pause()
        assert prompt.text == "abc\n"


async def test_ctrl_j_inserts_newline(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "abc"
        prompt.move_cursor((0, 3))
        await pilot.press("ctrl+j")
        await pilot.pause()
        assert prompt.text == "abc\n"
