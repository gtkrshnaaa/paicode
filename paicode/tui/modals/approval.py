from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ApprovalScreen(ModalScreen[bool]):
    BINDINGS = [("escape", "deny", "Deny")]

    def __init__(self, action: str, resource: str):
        super().__init__()
        self.action = action
        self.resource = resource

    def compose(self) -> ComposeResult:
        with Vertical(id="approval-card"):
            yield Label("Permission required", classes="modal-title")
            yield Static(f"Action: {self.action}", classes="approval-action")
            yield Static(self.resource[:1_000], classes="approval-resource")
            with Horizontal(classes="modal-actions"):
                yield Button("Allow", id="allow", variant="primary")
                yield Button("Deny", id="deny")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "allow")

    def action_deny(self) -> None:
        self.dismiss(False)
