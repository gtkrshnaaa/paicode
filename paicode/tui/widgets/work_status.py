import time

from rich.text import Text
from textual.widgets import Static


class WorkStatus(Static):
    BAR_WIDTH = 18

    def __init__(self):
        super().__init__("", id="chat-status")
        self._working = False
        self._stopping = False
        self._message = "idle"
        self._position = 0
        self._queue = 0
        self._started = 0.0

    @property
    def is_working(self) -> bool:
        return self._working

    @property
    def queue_count(self) -> int:
        return self._queue

    def on_mount(self) -> None:
        self.set_interval(0.15, self._tick)
        self._refresh_display()

    def begin(self) -> None:
        self._working = True
        self._stopping = False
        self._message = "thinking"
        self._started = time.monotonic()
        self._refresh_display()

    def end(self) -> None:
        self._working = False
        self._stopping = False
        self._message = "idle"
        self._refresh_display()

    def set_message(self, message: str) -> None:
        self._message = message or "thinking"
        self._refresh_display()

    def set_queue(self, count: int) -> None:
        self._queue = max(0, int(count))
        self._refresh_display()

    def set_stopping(self) -> None:
        self._stopping = True
        self._message = "stopping after current step"
        self._refresh_display()

    def _tick(self) -> None:
        if not self._working:
            return
        self._position = (self._position + 1) % self.BAR_WIDTH
        self._refresh_display()

    def _refresh_display(self) -> None:
        if not self._working:
            line = f"[{'-' * self.BAR_WIDTH}] idle"
            hint = "Esc stop | type to queue"
            self.update(Text(f"{line}\n{hint}", style="#8a8a8a"))
            return

        cells = ["-"] * self.BAR_WIDTH
        for offset in range(6):
            cells[(self._position + offset) % self.BAR_WIDTH] = "#"
        elapsed = int(time.monotonic() - self._started)
        first = f"[{''.join(cells)}] {self._message} {elapsed}s"
        if self._stopping:
            second = f"stopping now | queued {self._queue}"
        else:
            second = f"Esc to stop | queued {self._queue}"
        self.update(Text(f"{first}\n{second}", style="#8a8a8a"))
