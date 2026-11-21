from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea

from ..syntax import language_for_path
from ..theme import MONO_TEXTAREA



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
                language=language_for_path(self.path),
                id="preview-text",
            )
            with Horizontal(classes="modal-actions"):
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        area = self.query_one("#preview-text", TextArea)
        area.register_theme(MONO_TEXTAREA)
        area.theme = MONO_TEXTAREA.name
        area.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
