from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog
from rich.text import Text


class DiffPane(Vertical):
    def __init__(self):
        super().__init__(id="diff")

    def compose(self) -> ComposeResult:
        yield RichLog(id="diff-log", max_lines=5000, wrap=False, markup=False)

    def on_mount(self) -> None:
        self.border_title = "AI Diff"
        self.add_note("File changes produced by the agent appear here.")

    def _log(self) -> RichLog:
        return self.query_one("#diff-log", RichLog)

    def add_diff(self, path: str, diff: str) -> None:
        log = self._log()
        added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        log.write(Text(f"{path or 'change'}  +{added} -{removed}", style="bold #d4d4d4"))
        for line in diff.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                style = "bold #8a8a8a"
            elif line.startswith("+"):
                style = "#e5e5e5"
            elif line.startswith("-"):
                style = "#6b6b6b"
            elif line.startswith("@@"):
                style = "bold #8a8a8a"
            else:
                style = "#8a8a8a"
            log.write(Text(line, style=style))
        log.write(Text(""))

    def add_note(self, text: str) -> None:
        self._log().write(Text(text, style="#8a8a8a"))

    def clear(self) -> None:
        self._log().clear()
