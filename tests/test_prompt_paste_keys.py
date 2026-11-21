from pathlib import Path

import pytest
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


async def test_ctrl_shift_v_pastes_raw_text_only(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(prompt_module, "read_clipboard_text", lambda: "first\nsecond")
    monkeypatch.setattr(
        prompt_module,
        "read_clipboard_image",
        lambda: pytest.fail("Ctrl+Shift+V must not read clipboard images"),
    )
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await pilot.press("ctrl+shift+v")
        await pilot.pause()
        assert prompt.text == "first\nsecond"
        _, expanded, images = prompt.build_submission()
        assert expanded == "first\nsecond"
        assert images == []


async def test_ctrl_shift_v_replaces_selection(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(prompt_module, "read_clipboard_text", lambda: "XY")
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "abcd"
        prompt.move_cursor((0, 1))
        prompt.move_cursor((0, 3), select=True)
        await pilot.press("ctrl+shift+v")
        await pilot.pause()
        assert prompt.text == "aXYd"
        assert prompt.cursor_location == (0, 3)


async def test_ctrl_shift_v_ignores_image_only_clipboard(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(prompt_module, "read_clipboard_text", lambda: "")
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await pilot.press("ctrl+shift+v")
        await pilot.pause()
        assert prompt.text == ""
        _, _, images = prompt.build_submission()
        assert images == []


async def test_ctrl_shift_v_normalizes_crlf(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(
        prompt_module, "read_clipboard_text", lambda: "one\r\ntwo\rthree"
    )
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await pilot.press("ctrl+shift+v")
        await pilot.pause()
        assert prompt.text == "one\ntwo\nthree"
        assert prompt._target_height == 5


async def test_ctrl_shift_v_accepts_uppercase_kitty_key(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(prompt_module, "read_clipboard_text", lambda: "kitty paste")
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await prompt._on_key(sequence_to_key("\x1b[86;6u"))
        await pilot.pause()
        assert prompt.text == "kitty paste"


async def test_ctrl_v_keeps_image_first_behavior(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(
        prompt_module,
        "read_clipboard_image",
        lambda: ("image/png", b"fake-image"),
    )
    monkeypatch.setattr(
        prompt_module,
        "read_clipboard_text",
        lambda: pytest.fail("Ctrl+V must prefer clipboard images"),
    )
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await pilot.press("ctrl+v")
        await pilot.pause()
        assert prompt.text == "[image-1]"
        _, _, images = prompt.build_submission()
        assert len(images) == 1
        assert images[0].mime == "image/png"


async def test_bracketed_single_line_paste_inserts_text(
    project: Path, config_home: Path
):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await prompt._on_paste(events.Paste("bracketed text"))
        await pilot.pause()
        assert prompt.text == "bracketed text"
