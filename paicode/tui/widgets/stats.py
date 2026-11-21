from textual.widgets import Static
from rich.text import Text


class StatsBar(Static):
    def __init__(self):
        super().__init__("", id="stats")

    def update_stats(self, stats, provider: str, model: str, busy: bool) -> None:
        state = "working" if busy else "idle"
        left = f" {provider or 'no provider'} / {model or 'no model'} | {stats.summary()} | {state}"
        right = " ctrl+l clear  ctrl+r files  f1 help "
        self.update(Text(left + " " * 2 + right, style="#8a8a8a"))
