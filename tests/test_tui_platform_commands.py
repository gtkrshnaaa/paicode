from pathlib import Path

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp


async def test_platform_slash_commands(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt")
        for command in ["/mcp", "/rewind", "/hooks", "/policy", "/budget", "/telemetry", "/diagnostics"]:
            prompt.text = command
            await pilot.press("enter")
            await pilot.pause()
            assert app.busy is False
