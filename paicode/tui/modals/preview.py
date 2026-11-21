from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea


LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".sh": "bash",
    ".css": "css",
    ".html": "html",
    ".yaml": "yaml",
    ".yml": "yaml",
}


class FilePreviewScreen(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, path: Path, text: str):
        super().__init__()
        self.path = path
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="preview-card"):
            yield Label(str(self.path), classes="modal-title")
            yield TextArea(
                self.text,
                read_only=True,
                show_line_numbers=True,
                language=LANGUAGES.get(self.path.suffix.lower()),
                id="preview-text",
            )
            with Horizontal(classes="modal-actions"):
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        self.query_one("#preview-text", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
