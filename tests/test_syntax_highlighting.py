from pathlib import Path

from textual.widgets import TextArea

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.modals.preview import FilePreviewScreen
from paicode.tui.syntax import highlight_code, highlight_diff_line, language_for_path
from paicode.tui.theme import MONO_TEXTAREA


def test_language_detection_and_code_highlighting():
    assert language_for_path("app.py") == "python"
    assert language_for_path("view.tsx") == "typescript"
    assert language_for_path("Dockerfile") == "docker"
    text = highlight_code("def add(a, b):\n    return a + b", "python")
    assert text.plain.startswith("def add")
    assert len(text.spans) > 1


def test_diff_line_highlights_code_with_marker():
    text = highlight_diff_line("app.py", "+def add(a, b): return a + b")
    assert text.plain.startswith("+def add")
    assert len(text.spans) > 1
    removed = highlight_diff_line("app.py", "-old_value = 1")
    assert removed.plain.startswith("-old_value")
    hunk = highlight_diff_line("app.py", "@@ -1,2 +1,3 @@")
    assert hunk.plain.startswith("@@")


async def test_preview_uses_monochrome_syntax_theme(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause()
        app.push_screen(FilePreviewScreen(project / "sample.py", "def add(a, b):\n    return a + b\n"))
        await pilot.pause()
        area = app.screen.query_one("#preview-text", TextArea)
        assert area.theme == MONO_TEXTAREA.name
        assert area.language == "python"
        assert area.read_only is True
        assert area.show_line_numbers is True
