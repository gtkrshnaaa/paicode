from pathlib import Path

from textual import events
from textual._xterm_parser import XTermParser

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets import prompt as prompt_module
from paicode.tui.widgets.prompt import PromptInput


def sequence_to_key(sequence: str) -> events.Key:
    parsed = list(XTermParser().feed(sequence))
    assert len(parsed) == 1
    return parsed[0]


async def test_ctrl_shift_c_copies_full_prompt(
    project: Path, config_home: Path, monkeypatch
):
    written: list[str] = []
    monkeypatch.setattr(prompt_module, "write_clipboard_text", written.append)
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "copy the whole prompt"
        await pilot.press("ctrl+shift+c")
        await pilot.pause()
        assert app.clipboard == "copy the whole prompt"
        assert written == ["copy the whole prompt"]


async def test_ctrl_shift_c_copies_selection(
    project: Path, config_home: Path, monkeypatch
):
    written: list[str] = []
    monkeypatch.setattr(prompt_module, "write_clipboard_text", written.append)
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "abcdef"
        prompt.move_cursor((0, 2))
        prompt.move_cursor((0, 5), select=True)
        await pilot.press("ctrl+shift+c")
        await pilot.pause()
        assert app.clipboard == "cde"
        assert written == ["cde"]


async def test_ctrl_shift_c_empty_prompt_stays_empty(
    project: Path, config_home: Path, monkeypatch
):
    written: list[str] = []
    monkeypatch.setattr(prompt_module, "write_clipboard_text", written.append)
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = ""
        await pilot.press("ctrl+shift+c")
        await pilot.pause()
        assert app.clipboard == ""
        assert written == []


async def test_ctrl_shift_c_accepts_uppercase_kitty_key(
    project: Path, config_home: Path, monkeypatch
):
    written: list[str] = []
    monkeypatch.setattr(prompt_module, "write_clipboard_text", written.append)
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "uppercase key"
        await prompt._on_key(sequence_to_key("\x1b[67;6u"))
        await pilot.pause()
        assert app.clipboard == "uppercase key"
        assert written == ["uppercase key"]
