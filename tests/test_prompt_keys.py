import os
import stat
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


async def test_ctrl_shift_v_normalizes_crlf(
    project: Path, config_home: Path, monkeypatch
):
    monkeypatch.setattr(prompt_module, "read_clipboard_text", lambda: "one\r\ntwo\rthree")
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


async def test_clipboard_tools_round_trip_via_fake_wayland_binaries(
    project: Path, config_home: Path, monkeypatch, tmp_path: Path
):
    clipboard_file = tmp_path / "clipboard.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    copy_script = bin_dir / "wl-copy"
    copy_script.write_text(
        "#!/bin/sh\n"
        'cat > "$FAKE_CLIPBOARD_FILE"\n',
        encoding="utf-8",
    )
    paste_script = bin_dir / "wl-paste"
    paste_script.write_text(
        "#!/bin/sh\n"
        'cat "$FAKE_CLIPBOARD_FILE"\n',
        encoding="utf-8",
    )
    for script in (copy_script, paste_script):
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("FAKE_CLIPBOARD_FILE", str(clipboard_file))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    assert prompt_module.write_clipboard_text("round trip")
    assert prompt_module.read_clipboard_text() == "round trip"

    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        prompt.text = "copied through wl-copy"
        await pilot.press("ctrl+shift+c")
        await pilot.pause()
        assert clipboard_file.read_text(encoding="utf-8") == "copied through wl-copy"

        prompt.text = ""
        await pilot.press("ctrl+shift+v")
        await pilot.pause()
        assert prompt.text == "copied through wl-copy"
