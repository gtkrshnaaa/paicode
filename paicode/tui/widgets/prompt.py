import re
from dataclasses import dataclass
from pathlib import Path

from rich.cells import cell_len
from rich.style import Style
from textual import events
from textual.message import Message
from textual.strip import Strip
from textual.widgets import TextArea

from ...agent.attachments import MAX_IMAGE_BYTES, ImageAttachment
from ..clipboard import read_clipboard_image


@dataclass
class PasteAttachment:
    token: str
    text: str


IMAGE_SUFFIXES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

PLACEHOLDER_RE = re.compile(r"\[pasted \d+ lines?\]|\[image-\d+\]")
PLACEHOLDER_STYLE = Style(bgcolor="#3a3a3a", color="#f5f5f5", bold=True)


class PromptInput(TextArea):
    DEFAULT_PLACEHOLDER = "Message Paicode or /help. Shift+Enter newline. Ctrl+E expand. Ctrl+G image."
    BUSY_PLACEHOLDER = "Paicode is working. Type to queue a prompt."

    class Submitted(Message):
        def __init__(self, display: str, expanded: str, images: list[ImageAttachment]):
            self.display = display
            self.expanded = expanded
            self.images = images
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
        self._expanded = False
        self._pastes: list[PasteAttachment] = []
        self._images: list[ImageAttachment] = []
        self.suggestions_visible = False
        self.placeholder = self.DEFAULT_PLACEHOLDER

    def apply_completion(self, text: str) -> None:
        self.text = text
        self.move_cursor((0, len(text)))
        self.suggestions_visible = False
        self.focus()

    def build_submission(self) -> tuple[str, str, list[ImageAttachment]]:
        display = self.text
        expanded = self._expand_pastes(display)
        images = [image for image in self._images if image.token in display]
        images.sort(key=lambda image: display.find(image.token))
        return display, expanded, images

    def _expand_pastes(self, text: str) -> str:
        expanded = text
        for paste in self._pastes:
            if paste.token in expanded:
                expanded = expanded.replace(paste.token, paste.text, 1)
        return expanded

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
        if event.key == "ctrl+e":
            event.prevent_default()
            event.stop()
            self._expanded = not self._expanded
            self._fit_height()
            return
        if event.key == "ctrl+g":
            event.prevent_default()
            event.stop()
            result = read_clipboard_image()
            if result is None:
                self.app.notify("No image found in the clipboard.", severity="warning")
                return
            self._attach_image(*result)
            return
        if event.key == "enter" and not getattr(event, "shift", False):
            event.prevent_default()
            event.stop()
            self._submit()
            return
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            self._fit_height()
            return
        await super()._on_key(event)

    async def _on_paste(self, event: events.Paste) -> None:
        text = event.text
        if self._try_image_path(text):
            event.prevent_default()
            event.stop()
            return

        line_count = len(text.splitlines()) or 1
        if "\n" in text or "\r" in text or len(text) > 1200:
            unit = "line" if line_count == 1 else "lines"
            token = f"[pasted {line_count} {unit}]"
            self._pastes.append(PasteAttachment(token=token, text=text))
            self.insert(token)
            event.prevent_default()
            event.stop()
            return
        await super()._on_paste(event)

    def _try_image_path(self, text: str) -> bool:
        stripped = text.strip().strip("'\"")
        if not stripped or "\n" in stripped:
            return False
        path = Path(stripped).expanduser()
        if not path.is_file():
            return False
        mime = IMAGE_SUFFIXES.get(path.suffix.lower())
        if mime is None:
            return False
        try:
            data = path.read_bytes()
        except OSError:
            return False
        self._attach_image(mime, data)
        return True

    def _attach_image(self, mime: str, data: bytes) -> None:
        if len(data) > MAX_IMAGE_BYTES:
            self.app.notify("Image is larger than 10 MB.", severity="warning")
            return
        token = f"[image-{len(self._images) + 1}]"
        self._images.append(ImageAttachment(token=token, mime=mime, data=data))
        self.insert(token)

    def _submit(self) -> None:
        display, expanded, images = self.build_submission()
        self.post_message(self.Submitted(display, expanded, images))
        self.text = ""
        self._pastes.clear()
        self._images.clear()
        self._fit_height()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._fit_height()
        self.post_message(self.ContentChanged(self.text))

    def on_blur(self) -> None:
        if self.suggestions_visible:
            self.suggestions_visible = False
            self.post_message(self.SuggestionDismiss())

    def _fit_height(self) -> None:
        lines = self.text.count("\n") + 1
        height = 22 if self._expanded else min(max(3, lines + 2), 14)
        if height != self._target_height:
            self._target_height = height
            self.styles.height = height
            self.refresh(layout=True)

    def render_line(self, y: int) -> Strip:
        strip = super().render_line(y)
        try:
            line = self.document.get_line(y)
        except IndexError:
            return strip
        matches = list(PLACEHOLDER_RE.finditer(line))
        if not matches:
            return strip

        parts = []
        position = 0
        for match in matches:
            start = cell_len(line[: match.start()])
            end = min(start + cell_len(match.group()), strip.cell_length)
            if start >= strip.cell_length:
                break
            if start > position:
                parts.append(strip.crop(position, start))
            parts.append(strip.crop(start, end).apply_style(PLACEHOLDER_STYLE))
            position = end
        if position < strip.cell_length:
            parts.append(strip.crop(position))
        return Strip.join(parts) if parts else strip
