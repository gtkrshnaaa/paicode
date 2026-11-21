import fnmatch
from pathlib import Path

from ..core.paths import MAX_TEXT_BYTES, is_inside, resolve_system_path, system_path_block_reason
from .diff import looks_binary
from .types import ToolResult


class ExploreTools:
    def __init__(self, root: Path, stats):
        self.root = root
        self.stats = stats

    def explore(self, path: str, reason: str, pattern: str = "*", limit: int = 200) -> ToolResult:
        reason = (reason or "").strip()
        if len(reason) < 12:
            raise ValueError(
                "Provide a concrete reason of at least 12 characters for exploring outside the workspace."
            )

        target = resolve_system_path(path, self.root, must_exist=True)
        scope = "workspace" if is_inside(self.root, target) else "system"
        header = "\n".join(
            [
                f"Path: {target}",
                f"Scope: {scope}",
                f"Reason: {reason}",
            ]
        )
        if scope == "system":
            header += f"\nWrites remain confined to: {self.root}"

        if target.is_dir():
            return ToolResult(
                ok=True,
                output=header + "\n\n" + self._list_directory(target, pattern, limit),
                kind="explore",
            )
        if not target.is_file():
            raise ValueError("Path is not a regular file or directory.")

        if target.stat().st_size > MAX_TEXT_BYTES:
            raise ValueError(f"File is larger than {MAX_TEXT_BYTES} bytes.")
        raw = target.read_bytes()
        if looks_binary(raw):
            raise ValueError("Binary files cannot be explored.")
        text = raw.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        selected = lines[:2000]
        body = "\n".join(selected)
        if len(lines) > len(selected):
            body += f"\n... [truncated; {len(lines) - len(selected)} more lines]"
        self.stats.mark("read")
        return ToolResult(ok=True, output=f"{header}\n\n{body}", kind="explore")

    def _list_directory(self, directory: Path, pattern: str, limit: int) -> str:
        items = []
        hidden = 0
        try:
            entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError as exc:
            raise ValueError(f"Could not list directory: {exc}") from exc

        for entry in entries:
            if system_path_block_reason(entry):
                hidden += 1
                continue
            if pattern and pattern != "*" and not fnmatch.fnmatch(entry.name, pattern):
                continue
            try:
                if entry.is_dir():
                    items.append(f"dir  {entry.name}/")
                elif entry.is_file():
                    items.append(f"file {entry.name} ({entry.stat().st_size} bytes)")
                else:
                    items.append(f"other {entry.name}")
            except OSError:
                items.append(f"other {entry.name}")
            if len(items) >= max(1, min(int(limit or 200), 1000)):
                items.append("... [truncated by limit]")
                break

        if hidden:
            items.append(f"[{hidden} restricted entries hidden by policy]")
        if not items:
            return "Directory is empty or all entries were filtered."
        return "\n".join(items)
