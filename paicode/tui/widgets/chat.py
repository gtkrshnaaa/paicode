from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Markdown, Static
from rich.text import Text

from .work_status import WorkStatus


class AssistantMarkdown(Markdown):
    def __init__(self, markdown: str = "", **kwargs):
        super().__init__(markdown, **kwargs)
        self._pending_source = markdown

    def set_source(self, markdown: str) -> None:
        self._pending_source = markdown
        if self.is_mounted:
            self.update(markdown)

    async def _on_mount(self, event) -> None:
        await super()._on_mount(event)
        if self._pending_source:
            await self.update(self._pending_source)


class ChatPane(Vertical):
    def __init__(self):
        super().__init__(id="chat")
        self._stream: AssistantMarkdown | None = None
        self._assistant_card: Vertical | None = None
        self._buffer = ""
        self._assistant_entry: dict | None = None
        self._recording = True
        self._turn = 0
        self._sync_timer = None
        self.transcript: list[dict] = []

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-scroll")
        yield WorkStatus()

    def on_mount(self) -> None:
        self.border_title = "Chat"

    def _scroll(self) -> VerticalScroll:
        return self.query_one("#chat-scroll", VerticalScroll)

    def _status(self) -> WorkStatus:
        return self.query_one(WorkStatus)

    def begin_work(self) -> None:
        self._status().begin()

    def end_work(self) -> None:
        self._status().end()

    def set_work_message(self, message: str) -> None:
        self._status().set_message(message)

    def set_queue(self, count: int) -> None:
        self._status().set_queue(count)

    def set_stopping(self) -> None:
        self._status().set_stopping()

    def _record(self, entry: dict) -> None:
        if self._recording:
            self.transcript.append(entry)

    def _turn_divider(self) -> Text:
        text = Text(no_wrap=True, overflow="crop")
        text.append("──", style="#1f1f1f")
        text.append(f" TURN {self._turn:02d} ", style="bold #8a8a8a")
        text.append("· ", style="#3a3a3a")
        text.append(f"{datetime.now().strftime('%H:%M')} ", style="#6b6b6b")
        text.append("─" * 220, style="#1f1f1f")
        return text

    def add_user(self, text: str) -> None:
        self.end_assistant()
        self._turn += 1
        if self._turn > 1:
            self._scroll().mount(Static(self._turn_divider(), classes="turn-divider"))
        self._record({"kind": "user", "text": text})
        content = Text()
        content.append("YOU", style="bold #f5f5f5")
        content.append("  prompt\n", style="#6b6b6b")
        content.append(text, style="#d4d4d4")
        self._scroll().mount(Static(content, classes="msg user"))
        self._scroll().scroll_end(animate=False)

    def add_system(self, text: str) -> None:
        self.end_assistant()
        self._record({"kind": "system", "text": text})
        content = Text()
        content.append("· ", style="#3a3a3a")
        content.append(text, style="#7a7a7a")
        self._scroll().mount(Static(content, classes="msg system"))
        self._scroll().scroll_end(animate=False)

    def add_markdown_system(self, markdown: str, plain_text: str = "") -> None:
        self.end_assistant()
        self._record({"kind": "system", "text": plain_text or markdown})
        widget = Markdown(markdown, classes="msg system md")
        scroll = self._scroll()
        scroll.mount(widget)
        scroll.scroll_to_widget(widget, top=True, animate=False)

    def _tool_text(self, name: str, status: str, detail: str) -> Text:
        style = "#e5e5e5" if status == "ok" else "#8a8a8a" if status == "failed" else "#6b6b6b"
        first_line = (detail or "").splitlines()[0][:220] if detail else ""
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append("• ", style="#4a4a4a")
        text.append(f"{name} ", style="bold #d4d4d4")
        text.append(status, style=style)
        if first_line:
            text.append(f"  {first_line}", style="#8a8a8a")
        return text

    def add_tool(self, name: str, status: str, detail: str = "") -> Static:
        self.end_assistant()
        self._record(
            {
                "kind": "tool",
                "name": name,
                "status": status,
                "detail": (detail or "").splitlines()[0][:220] if detail else "",
            }
        )
        widget = Static(self._tool_text(name, status, detail), classes="msg tool")
        self._scroll().mount(widget)
        self._scroll().scroll_end(animate=False)
        return widget

    def update_tool(self, widget: Static, name: str, status: str, detail: str = "") -> None:
        for entry in reversed(self.transcript):
            if entry.get("kind") == "tool" and entry.get("status") == "running":
                entry.update(
                    {
                        "name": name,
                        "status": status,
                        "detail": (detail or "").splitlines()[0][:220] if detail else "",
                    }
                )
                break
        widget.update(self._tool_text(name, status, detail))
        self._scroll().scroll_end(animate=False)

    def _new_assistant_card(self, text: str = "") -> tuple[Vertical, AssistantMarkdown]:
        stream = AssistantMarkdown(text, classes="assistant-body")
        label = Text()
        label.append("PAI", style="bold #f5f5f5")
        label.append("  assistant", style="#6b6b6b")
        label.append(f"  ·  {datetime.now().strftime('%H:%M')}", style="#4a4a4a")
        card = Vertical(Static(label, classes="role"), stream, classes="msg assistant-card")
        return card, stream

    def begin_assistant(self) -> None:
        self._buffer = ""
        self._assistant_entry = None
        self._assistant_card = None
        self._stream = None

    def _schedule_stream_sync(self, stream=None, buffer: str | None = None) -> None:
        stream = stream or self._stream
        if stream is None:
            return
        text = self._buffer if buffer is None else buffer
        if self._sync_timer is not None:
            self._sync_timer.stop()
        self._sync_timer = self.set_timer(0.05, lambda: stream.set_source(text))

    def append_assistant(self, chunk: str) -> None:
        self._buffer += chunk
        if self._stream is None:
            self._assistant_card, self._stream = self._new_assistant_card(self._buffer)
            self._scroll().mount(self._assistant_card)
        else:
            self._stream.set_source(self._buffer)
        self._schedule_stream_sync()
        if self._assistant_entry is None:
            self._assistant_entry = {"kind": "assistant", "text": ""}
            self._record(self._assistant_entry)
        self._assistant_entry["text"] = self._buffer
        self._scroll().scroll_end(animate=False)

    def add_assistant(self, text: str) -> None:
        if not text:
            return
        self._record({"kind": "assistant", "text": text})
        card, stream = self._new_assistant_card(text)
        self._scroll().mount(card)
        self._buffer = text
        self._stream = stream
        self._schedule_stream_sync()
        self._scroll().scroll_end(animate=False)

    def end_assistant(self) -> None:
        stream = self._stream
        buffer = self._buffer
        if stream is not None and buffer.strip():
            self._schedule_stream_sync(stream, buffer)
        elif self._sync_timer is not None:
            self._sync_timer.stop()
        self._sync_timer = None
        if self._assistant_card is not None and not self._buffer.strip():
            self._assistant_card.remove()
        if self._assistant_entry is not None:
            if self._buffer.strip():
                self._assistant_entry["text"] = self._buffer
            elif self._assistant_entry in self.transcript:
                self.transcript.remove(self._assistant_entry)
        self._stream = None
        self._assistant_card = None
        self._buffer = ""
        self._assistant_entry = None

    def reset_transcript(self) -> None:
        self.transcript = []
        self._turn = 0

    def clear(self, clear_transcript: bool = True) -> None:
        if self._sync_timer is not None:
            self._sync_timer.stop()
            self._sync_timer = None
        scroll = self._scroll()
        for child in list(scroll.children):
            child.remove()
        self._stream = None
        self._assistant_card = None
        self._buffer = ""
        self._assistant_entry = None
        self._turn = 0
        if clear_transcript:
            self.transcript = []

    def restore(self, entries: list[dict]) -> None:
        self.clear()
        self._turn = 0
        self._recording = False
        for entry in entries:
            kind = entry.get("kind")
            if kind == "user":
                self.add_user(str(entry.get("text", "")))
            elif kind == "system":
                self.add_system(str(entry.get("text", "")))
            elif kind == "tool":
                self.add_tool(
                    str(entry.get("name", "")),
                    str(entry.get("status", "ok")),
                    str(entry.get("detail", "")),
                )
            elif kind == "assistant":
                self.add_assistant(str(entry.get("text", "")))
        self.transcript = list(entries)
        self._recording = True
        self._scroll().scroll_end(animate=False)
