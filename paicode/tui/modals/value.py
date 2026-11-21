from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class ValueModal(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, title: str, label: str, placeholder: str = "", password: bool = False, value: str = ""):
        super().__init__()
        self.title_text = title
        self.label_text = label
        self.placeholder = placeholder
        self.password = password
        self.value = value

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label(self.title_text, classes="modal-title")
            yield Input(
                placeholder=self.placeholder,
                value=self.value,
                password=self.password,
                id="value-input",
            )
            with Horizontal(classes="modal-actions"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#value-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.dismiss(self.query_one("#value-input", Input).value.strip() or None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
