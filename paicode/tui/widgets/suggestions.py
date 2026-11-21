from rich.console import Group
from rich.text import Text
from textual.widgets import Static

from ..commands import SlashCommandSpec


class SuggestionBar(Static):
    WINDOW = 8

    def __init__(self):
        super().__init__("", id="suggestions")
        self._items: list[SlashCommandSpec] = []
        self._selected = 0
        self.styles.display = "none"

    @property
    def has_suggestions(self) -> bool:
        return bool(self._items)

    @property
    def selected_index(self) -> int:
        return self._selected

    def show(self, items: list[SlashCommandSpec], selected: int) -> None:
        self._items = list(items)
        self._selected = max(0, min(selected, len(self._items) - 1))
        self.update(self._build())
        self.styles.display = "block"

    def hide(self) -> None:
        self._items = []
        self._selected = 0
        self.update("")
        self.styles.display = "none"

    def _build(self):
        if not self._items:
            return ""

        selected = self._selected
        start = max(0, min(selected - self.WINDOW // 2, max(0, len(self._items) - self.WINDOW)))
        visible = self._items[start : start + self.WINDOW]
        lines = []
        if start > 0:
            lines.append(Text("  ...", style="#6b6b6b"))
        for offset, item in enumerate(visible):
            index = start + offset
            is_selected = index == selected
            row = Text(no_wrap=True, overflow="ellipsis")
            row.append("> " if is_selected else "  ", style="bold #e5e5e5" if is_selected else "#6b6b6b")
            row.append(f"{item.usage:<24}", style="bold #e5e5e5" if is_selected else "#d4d4d4")
            row.append(item.description, style="#e5e5e5" if is_selected else "#8a8a8a")
            if is_selected:
                row.stylize("on #262626")
            lines.append(row)
        if start + self.WINDOW < len(self._items):
            lines.append(Text("  ...", style="#6b6b6b"))
        return Group(*lines)
