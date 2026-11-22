from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from ...providers.presets import get_preset


class ProviderModal(ModalScreen[dict | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, default_name: str = "", default_url: str = ""):
        super().__init__()
        self.default_name = default_name.strip().lower()
        self.default_url = default_url.strip()

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Connect provider", classes="modal-title")
            yield Static("Presets: deepseek, openai, openrouter, google, custom", classes="hint")
            yield Input(placeholder="Provider name", value=self.default_name, id="provider-name")
            yield Input(placeholder="Base URL", id="provider-url")
            yield Input(placeholder="API key", password=True, id="provider-key")
            yield Static("", id="provider-error", classes="error")
            with Horizontal(classes="modal-actions"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        preset = get_preset(self.default_name)
        if self.default_url:
            self.query_one("#provider-url", Input).value = self.default_url
        elif preset:
            self.query_one("#provider-url", Input).value = preset.base_url
        self.query_one("#provider-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        name = self.query_one("#provider-name", Input).value.strip()
        url = self.query_one("#provider-url", Input).value.strip()
        key = self.query_one("#provider-key", Input).value.strip()
        if not name:
            self.query_one("#provider-error", Static).update("Provider name is required.")
            return
        if not url:
            preset = get_preset(name)
            url = preset.base_url if preset else ""
        if not url:
            self.query_one("#provider-error", Static).update("Base URL is required.")
            return
        self.dismiss({"name": name, "base_url": url, "api_key": key})

    def action_cancel(self) -> None:
        self.dismiss(None)
