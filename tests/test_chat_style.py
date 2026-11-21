from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Markdown, Static

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp


async def test_chat_message_cards_and_markdown(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        app.chat.add_user("Explain the deployment flow.")
        app.chat.add_assistant(
            "## Deployment\n\nUse **Docker** and `deploy.sh`.\n\n"
            "```bash\ndocker build -t app .\n```\n\n"
            "| Step | Command |\n| --- | --- |\n| Test | ./test.sh |"
        )
        app.chat.add_markdown_system("## Sessions\n\n- **`s-demo`** · demo")
        app.chat.add_tool("read", "ok", "index.html (lines 1-40 of 373)")
        await pilot.pause()
        await pilot.pause()

        children = list(app.chat._scroll().children)
        assert any(isinstance(child, Static) and "user" in child.classes for child in children)
        cards = [
            child
            for child in children
            if isinstance(child, Vertical) and "assistant-card" in child.classes
        ]
        assert len(cards) == 1
        assert cards[0].query_one(Markdown) is not None
        assert any(
            isinstance(child, Markdown) and "md" in child.classes for child in children
        )
        tools = [child for child in children if "tool" in child.classes]
        assert tools
        assert tools[0].size.height == 1
