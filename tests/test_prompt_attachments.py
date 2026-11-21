from pathlib import Path

from textual import events

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets.prompt import PromptInput


async def test_multiline_paste_marker_and_expansion(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        pasted = "first line\nsecond line\nthird line"
        await prompt._on_paste(events.Paste(pasted))
        await pilot.pause()
        assert prompt.text == "[pasted 3 lines]"
        display, expanded, images = prompt.build_submission()
        assert display == "[pasted 3 lines]"
        assert expanded == pasted
        assert images == []


async def test_image_path_paste_becomes_attachment(project: Path, config_home: Path):
    image = project / "diagram.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        await prompt._on_paste(events.Paste(str(image)))
        await pilot.pause()
        assert prompt.text == "[image-1]"
        display, expanded, images = prompt.build_submission()
        assert display == "[image-1]"
        assert expanded == "[image-1]"
        assert len(images) == 1
        assert images[0].mime == "image/png"
        assert images[0].data_url.startswith("data:image/png;base64,")


async def test_ctrl_e_toggles_expanded_prompt(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", PromptInput)
        prompt.focus()
        await pilot.press("ctrl+e")
        await pilot.pause()
        assert prompt._target_height == 22
        await pilot.press("ctrl+e")
        await pilot.pause()
        assert prompt._target_height == 3
