from pathlib import Path

from textual.widgets import Input, Tree

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp


async def test_tui_layout_and_slash_commands(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        assert app.query_one("#explorer") is not None
        assert app.query_one("#diff") is not None
        assert app.query_one("#chat") is not None
        assert app.query_one("#stats") is not None
        assert app.query_one("#prompt", Input) is not None
        tree = app.query_one("#file-tree", Tree)
        assert str(tree.root.label) == project.name

        app.query_one("#prompt", Input).value = "/help"
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.chat._scroll().children) >= 2

        app.query_one("#prompt", Input).value = "/stats"
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.chat._scroll().children) >= 3

        app.query_one("#prompt", Input).value = "/refresh"
        await pilot.press("enter")
        await pilot.pause()
        assert app.focused is app.query_one("#prompt", Input)

        app.query_one("#prompt", Input).value = "/init"
        await pilot.press("enter")
        await pilot.pause()
        assert (project / "PAICODE.md").is_file()

        app.query_one("#prompt", Input).value = "/model deepseek-flash"
        await pilot.press("enter")
        await pilot.pause()
        assert app.busy is False

        screenshot = app.export_screenshot()
        assert screenshot.startswith("<svg")
