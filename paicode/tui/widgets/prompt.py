from textual import events
from textual.message import Message
from textual.widgets import TextArea


class PromptInput(TextArea):
    class Submitted(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_height = 3

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter" and not getattr(event, "shift", False):
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self.text))
            self.text = ""
            self._fit_height()
            return
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            self._fit_height()
            return
        await super()._on_key(event)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._fit_height()

    def _fit_height(self) -> None:
        lines = self.text.count("\n") + 1
        height = min(max(3, lines + 2), 14)
        if height != self._target_height:
            self._target_height = height
            self.styles.height = height
            self.refresh(layout=True)
