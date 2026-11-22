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


async def test_approval_dialog_allows_action(project: Path, config_home: Path):
    import threading

    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        result = {}
        worker = threading.Thread(
            target=lambda: result.update(allowed=app._approve_action("shell", "echo hello"))
        )
        worker.start()
        await pilot.pause(0.3)
        await pilot.click("#allow")
        worker.join(timeout=5)
        assert result["allowed"] is True
