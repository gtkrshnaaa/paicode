from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option


class ModelModal(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, models: list[str], current: str = ""):
        super().__init__()
        self.models = models
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Select model", classes="modal-title")
            options = [
                Option(f"{model}  (current)" if model == self.current else model, id=model)
                for model in self.models
            ]
            yield OptionList(*options, id="model-list")

    def on_mount(self) -> None:
        self.query_one("#model-list", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id))

    def action_cancel(self) -> None:
        self.dismiss(None)
