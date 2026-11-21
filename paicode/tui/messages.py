from pathlib import Path

from textual.message import Message


class FileSelected(Message):
    def __init__(self, path: Path):
        self.path = path
        super().__init__()
