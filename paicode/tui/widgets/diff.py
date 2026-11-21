from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog
from rich.text import Text


class DiffPane(Vertical):
    def __init__(self):
        super().__init__(id="diff")
        self._count = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="diff-log", max_lines=5000, wrap=False, markup=False)

    def on_mount(self) -> None:
        self.border_title = "AI Diff"
        self.add_note("AI diff history for this session appears here.")

    def _log(self) -> RichLog:
        return self.query_one("#diff-log", RichLog)

    def _divider(self, label: str, meta: str = "") -> Text:
        text = Text(no_wrap=True, overflow="crop")
        text.append("──", style="#1f1f1f")
        text.append(f" {label} ", style="bold #e5e5e5")
        if meta:
            text.append(f" {meta} ", style="#6b6b6b")
        used = 4 + len(label) + (len(meta) + 2 if meta else 0)
        text.append("─" * max(8, 220 - used), style="#1f1f1f")
        text.append("──", style="#1f1f1f")
        return text

    def add_diff(self, path: str, diff: str, timestamp: str = "") -> None:
        log = self._log()
        added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        log.write(Text(""))
        self._count += 1
        meta = f"+{added} -{removed}"
        if timestamp:
            meta += f"  {timestamp}"
        log.write(self._divider(f"DIFF {self._count:02d}  {path or 'change'}", meta))
        for line in diff.splitlines():
            text = Text(line, no_wrap=True, overflow="crop")
            if line.startswith("+++") or line.startswith("---"):
                text.stylize("bold #6b6b6b")
            elif line.startswith("+"):
                text.stylize("#e5e5e5 on #121212")
            elif line.startswith("-"):
                text.stylize("#8a8a8a on #0e0e0e")
            elif line.startswith("@@"):
                text.stylize("bold #bdbdbd")
            else:
                text.stylize("#707070")
            log.write(text)

    def add_note(self, text: str) -> None:
        self._log().write(Text(f"· {text}", style="#6b6b6b"))

    def clear(self) -> None:
        self._count = 0
        self._log().clear()
