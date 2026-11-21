from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Tree

from ...core.paths import EXCLUDED_DIRS, SENSITIVE_NAMES
from ..messages import FileSelected


@dataclass
class ExplorerItem:
    path: Path
    depth: int


class ExplorerPane(Vertical):
    MAX_NODES = 700

    def __init__(self, root: Path):
        super().__init__(id="explorer")
        self.root = root
        self._node_count = 0

    def compose(self) -> ComposeResult:
        yield Tree("Project", id="file-tree")

    def on_mount(self) -> None:
        self.border_title = "Files"
        self.refresh_tree()

    def refresh_tree(self) -> None:
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        self._node_count = 0
        tree.root.label = self.root.name
        self._populate(tree.root, self.root, 0)
        tree.root.expand()

    def _populate(self, node, directory: Path, depth: int) -> None:
        if depth > 6 or self._node_count >= self.MAX_NODES:
            return
        try:
            entries = [
                entry
                for entry in directory.iterdir()
                if entry.name not in EXCLUDED_DIRS and entry.name not in SENSITIVE_NAMES
            ]
        except OSError:
            return
        entries.sort(key=lambda item: (not item.is_dir(), item.name.lower()))
        for entry in entries[:200]:
            if self._node_count >= self.MAX_NODES:
                return
            self._node_count += 1
            item = ExplorerItem(entry, depth + 1)
            if entry.is_dir():
                node.add(f"{entry.name}/", data=item, expand=False)
            else:
                node.add(entry.name, data=item, allow_expand=False)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        item = event.node.data
        if not isinstance(item, ExplorerItem) or not item.path.is_dir():
            return
        if event.node.children:
            return
        self._populate(event.node, item.path, item.depth)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        item = event.node.data
        if isinstance(item, ExplorerItem) and item.path.is_file():
            self.post_message(FileSelected(item.path))
