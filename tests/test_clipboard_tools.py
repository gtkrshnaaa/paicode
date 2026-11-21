import os
import stat
from pathlib import Path

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets import prompt as prompt_module
from paicode.tui.widgets.prompt import PromptInput


async def test_clipboard_text_reader_rejects_image_bytes(
    monkeypatch, tmp_path: Path
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    image_file = tmp_path / "image.bin"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    script = bin_dir / "wl-paste"
    script.write_text(
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *\"--type text/plain;charset=utf-8\"*|*\"--type text/plain\"*|*\"--type UTF8_STRING\"*) exit 1 ;;\n"
        "esac\n"
        'cat "$FAKE_IMAGE_FILE"\n',
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("FAKE_IMAGE_FILE", str(image_file))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    assert prompt_module.read_clipboard_text() == ""


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
