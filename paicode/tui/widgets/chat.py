from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Markdown, Static
from rich.text import Text


class ChatPane(Vertical):
    def __init__(self):
        super().__init__(id="chat")
        self._stream: Markdown | None = None
        self._buffer = ""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-scroll")

    def on_mount(self) -> None:
        self.border_title = "Chat"

    def _scroll(self) -> VerticalScroll:
        return self.query_one("#chat-scroll", VerticalScroll)

    def add_user(self, text: str) -> None:
        content = Text.assemble(("You\n", "bold #8a8a8a"), (text, "#d4d4d4"))
        self._scroll().mount(Static(content, classes="msg user"))
        self._scroll().scroll_end(animate=False)

    def add_system(self, text: str) -> None:
        self._scroll().mount(Static(Text(text, style="#8a8a8a"), classes="msg system"))
        self._scroll().scroll_end(animate=False)

    def _tool_text(self, name: str, status: str, detail: str) -> Text:
        style = "#e5e5e5" if status == "ok" else "#8a8a8a" if status == "failed" else "#6b6b6b"
        first_line = (detail or "").splitlines()[0][:220] if detail else ""
        return Text.assemble(
            (f"{name} ", "bold #d4d4d4"),
            (status, style),
            (f"  {first_line}" if first_line else "", "#8a8a8a"),
        )

    def add_tool(self, name: str, status: str, detail: str = "") -> Static:
        widget = Static(self._tool_text(name, status, detail), classes="msg tool")
        self._scroll().mount(widget)
        self._scroll().scroll_end(animate=False)
        return widget

    def update_tool(self, widget: Static, name: str, status: str, detail: str = "") -> None:
        widget.update(self._tool_text(name, status, detail))
        self._scroll().scroll_end(animate=False)

    def begin_assistant(self) -> None:
        self._buffer = ""
        self._stream = Markdown("", classes="msg assistant")
        self._scroll().mount(self._stream)
        self._scroll().scroll_end(animate=False)

    def append_assistant(self, chunk: str) -> None:
        if self._stream is None:
            self.begin_assistant()
        self._buffer += chunk
        self._stream.update(self._buffer)
        self._scroll().scroll_end(animate=False)

    def end_assistant(self) -> None:
        if self._stream is not None and not self._buffer.strip():
            self._stream.remove()
        self._stream = None
        self._buffer = ""

    def clear(self) -> None:
        scroll = self._scroll()
        for child in list(scroll.children):
            child.remove()
        self._stream = None
        self._buffer = ""
