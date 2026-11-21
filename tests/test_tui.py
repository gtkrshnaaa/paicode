from pathlib import Path

from textual.widgets import Tree

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets.prompt import PromptInput


async def test_tui_layout_and_slash_commands(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        assert app.query_one("#explorer") is not None
        assert app.query_one("#diff") is not None
        assert app.query_one("#chat") is not None
        assert app.query_one("#stats") is not None
        assert app.query_one("#prompt", PromptInput) is not None
        assert app.theme == "paicode-mono"
        assert len(app.query(".pane-title")) == 0
        tree = app.query_one("#file-tree", Tree)
        assert str(tree.root.label) == project.name

        prompt = app.query_one("#prompt", PromptInput)
        prompt.text = "one\ntwo\nthree"
        await pilot.pause()
        assert prompt._target_height == 5
        prompt.text = "\n".join("line" for _ in range(20))
        await pilot.pause()
        assert prompt._target_height == 14
        prompt.text = ""
        prompt.focus()
        await pilot.press("a", "b", "c")
        await pilot.pause()
        assert prompt.text == "abc"
        await pilot.press("shift+enter")
        await pilot.pause()
        assert prompt.text == "abc\n"
        assert prompt._target_height == 4
        prompt.text = ""
        await pilot.pause()
        assert prompt._target_height == 3

        app.query_one("#prompt", PromptInput).text = "/help"
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.chat._scroll().children) >= 2

        app.query_one("#prompt", PromptInput).text = "/stats"
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.chat._scroll().children) >= 3

        app.query_one("#prompt", PromptInput).text = "/limits"
        await pilot.press("enter")
        await pilot.pause()

        app.query_one("#prompt", PromptInput).text = "/refresh"
        await pilot.press("enter")
        await pilot.pause()
        assert app.focused is app.query_one("#prompt", PromptInput)

        app.query_one("#prompt", PromptInput).text = "/init"
        await pilot.press("enter")
        await pilot.pause()
        assert (project / "PAICODE.md").is_file()

        app.query_one("#prompt", PromptInput).text = "/model deepseek-flash"
        await pilot.press("enter")
        await pilot.pause()
        assert app.busy is False

        screenshot = app.export_screenshot()
        assert screenshot.startswith("<svg")
