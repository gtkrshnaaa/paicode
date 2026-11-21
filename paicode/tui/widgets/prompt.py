from textual import events
from textual.message import Message
from textual.widgets import TextArea


class PromptInput(TextArea):
    class Submitted(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    class ContentChanged(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    class SuggestionNavigate(Message):
        def __init__(self, delta: int):
            self.delta = delta
            super().__init__()

    class SuggestionAccept(Message):
        pass

    class SuggestionDismiss(Message):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_height = 3
        self.suggestions_visible = False

    def apply_completion(self, text: str) -> None:
        self.text = text
        self.move_cursor((0, len(text)))
        self.suggestions_visible = False
        self.focus()

    async def _on_key(self, event: events.Key) -> None:
        if self.suggestions_visible:
            if event.key == "down":
                event.prevent_default()
                event.stop()
                self.post_message(self.SuggestionNavigate(1))
                return
            if event.key == "up":
                event.prevent_default()
                event.stop()
                self.post_message(self.SuggestionNavigate(-1))
                return
            if event.key == "tab":
                event.prevent_default()
                event.stop()
                self.post_message(self.SuggestionAccept())
                return
            if event.key == "escape":
                event.prevent_default()
                event.stop()
                self.post_message(self.SuggestionDismiss())
                return
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
        self.post_message(self.ContentChanged(self.text))

    def on_blur(self) -> None:
        if self.suggestions_visible:
            self.suggestions_visible = False
            self.post_message(self.SuggestionDismiss())

    def _fit_height(self) -> None:
        lines = self.text.count("\n") + 1
        height = min(max(3, lines + 2), 14)
        if height != self._target_height:
            self._target_height = height
            self.styles.height = height
            self.refresh(layout=True)
