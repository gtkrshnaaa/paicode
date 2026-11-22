import json
import os
import shutil
import stat
from pathlib import Path

from ..checkpoints import CheckpointStore
from ..core.atomic import atomic_write_text
from ..core.errors import PathSecurityError
from ..core.paths import EXCLUDED_DIRS, MAX_TEXT_BYTES, SENSITIVE_NAMES, display_path, resolve_in_root
from .diff import looks_binary, unified_diff
from .types import ToolResult


def _clear_bytecode(path: Path) -> None:
    if path.suffix != ".py":
        return
    cache = path.parent / "__pycache__"
    if not cache.is_dir():
        return
    for candidate in cache.glob(f"{path.stem}.*.pyc"):
        try:
            candidate.unlink()
        except OSError:
            pass


class FileTools:
    def __init__(self, root: Path, stats, allowed_write_paths: set[Path] | None = None, checkpoints: CheckpointStore | None = None):
        self.root = root
        self.stats = stats
        self.checkpoints = checkpoints or CheckpointStore(root)
        self.allowed_write_paths = (
            {path.resolve() for path in allowed_write_paths}
            if allowed_write_paths is not None
            else None
        )

    def _check_write(self, target: Path, allow_parent: bool = False) -> None:
        if self.allowed_write_paths is None:
            return
        resolved = target.resolve()
        if resolved in self.allowed_write_paths:
            return
        if allow_parent and any(resolved in allowed.parents for allowed in self.allowed_write_paths):
            return
        raise PathSecurityError(
            f"Agent does not own write path '{display_path(self.root, resolved)}'."
        )

    def _read_text(self, path: Path) -> str:
        if not path.is_file():
            raise ValueError(f"'{display_path(self.root, path)}' is not a file.")
        if path.stat().st_size > MAX_TEXT_BYTES:
            raise ValueError(f"File is larger than {MAX_TEXT_BYTES} bytes.")
        raw = path.read_bytes()
        if looks_binary(raw):
            raise ValueError("Binary files are not supported.")
        return raw.decode("utf-8", errors="ignore")

    def read(self, path: str, offset: int = 1, limit: int = 2000) -> ToolResult:
        target = resolve_in_root(self.root, path, must_exist=True)
        text = self._read_text(target)
        lines = text.splitlines()
        start = max(1, int(offset or 1))
        count = min(max(1, int(limit or 2000)), 20_000)
        selected = lines[start - 1 : start - 1 + count]
        header = f"# {display_path(self.root, target)} (lines {start}-{start + len(selected) - 1} of {len(lines)})"
        body = "\n".join(selected)
        if start - 1 + count < len(lines):
            body += f"\n... [truncated; {len(lines) - (start - 1 + count)} more lines]"
        self.stats.mark("read")
        return ToolResult(ok=True, output=f"{header}\n{body}", kind="read")

    def write(self, path: str, content: str) -> ToolResult:
        if len(content) > 20_000_000:
            raise ValueError("Content exceeds the 20,000,000 character limit.")
        target = resolve_in_root(self.root, path)
        self._check_write(target)
        old = ""
        existed = target.exists()
        if existed:
            if target.is_dir():
                raise ValueError("Target is a directory.")
            old = self._read_text(target)
        self.checkpoints.capture([target])
        mode = stat.S_IMODE(target.stat().st_mode) if existed else 0o644
        atomic_write_text(target, content, mode=mode)
        _clear_bytecode(target)
        diff, added, removed = unified_diff(old, content, display_path(self.root, target))
        self.stats.mark("edited" if existed else "created")
        output = f"{'Updated' if existed else 'Created'} {display_path(self.root, target)} (+{added} -{removed})"
        warning = self._syntax_check(target, content)
        if warning:
            output += f"\nSyntax check failed:\n{warning}"
        return ToolResult(
            ok=True,
            output=output,
            diff=diff,
            changed=[display_path(self.root, target)],
            kind="edited" if existed else "created",
        )

    def edit(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        target = resolve_in_root(self.root, path, must_exist=True)
        self._check_write(target)
        text = self._read_text(target)
        if old_string == new_string:
            raise ValueError("old_string and new_string are identical.")
        occurrences = text.count(old_string)
        if occurrences == 0:
            raise ValueError("old_string was not found in the file.")
        if occurrences > 1 and not replace_all:
            raise ValueError(
                f"old_string is ambiguous ({occurrences} matches). Provide more context or set replace_all."
            )
        updated = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
        self.checkpoints.capture([target])
        mode = stat.S_IMODE(target.stat().st_mode)
        atomic_write_text(target, updated, mode=mode)
        _clear_bytecode(target)
        diff, added, removed = unified_diff(text, updated, display_path(self.root, target))
        self.stats.mark("edited")
        output = f"Edited {display_path(self.root, target)} (+{added} -{removed})"
        warning = self._syntax_check(target, updated)
        if warning:
            output += f"\nSyntax check failed:\n{warning}"
        return ToolResult(
            ok=True,
            output=output,
            diff=diff,
            changed=[display_path(self.root, target)],
            kind="edited",
        )

    def list_dir(self, path: str = ".") -> ToolResult:
        target = resolve_in_root(self.root, path, must_exist=True)
        if not target.is_dir():
            raise ValueError("Target is not a directory.")
        entries = []
        for entry in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if entry.name in EXCLUDED_DIRS or entry.name in SENSITIVE_NAMES:
                continue
            entries.append(f"{entry.name}/" if entry.is_dir() else entry.name)
            if len(entries) >= 5_000:
                entries.append("... [truncated at 5,000 entries]")
                break
        label = display_path(self.root, target) or "."
        return ToolResult(ok=True, output=f"{label}/\n" + "\n".join(entries), kind="list")

    def mkdir(self, path: str) -> ToolResult:
        target = resolve_in_root(self.root, path)
        self._check_write(target, allow_parent=True)
        target.mkdir(parents=True, exist_ok=True)
        return ToolResult(ok=True, output=f"Created directory {display_path(self.root, target)}", kind="mkdir")

    def move(self, source: str, destination: str) -> ToolResult:
        src = resolve_in_root(self.root, source, must_exist=True)
        dest = resolve_in_root(self.root, destination)
        self._check_write(src)
        self._check_write(dest, allow_parent=True)
        if dest.exists():
            raise ValueError(f"Destination '{destination}' already exists.")
        self.checkpoints.capture([src, dest])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return ToolResult(
            ok=True,
            output=f"Moved {display_path(self.root, src)} to {display_path(self.root, dest)}",
            changed=[display_path(self.root, dest)],
            kind="move",
        )

    def delete(self, path: str, recursive: bool = False) -> ToolResult:
        target = resolve_in_root(self.root, path, must_exist=True)
        self._check_write(target)
        if target == self.root.resolve():
            raise ValueError("Refusing to delete the project root.")
        captured = list(target.rglob("*")) if target.is_dir() else [target]
        self.checkpoints.capture([item for item in captured if item.is_file()])
        if target.is_dir():
            if recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
        else:
            target.unlink()
        return ToolResult(ok=True, output=f"Deleted {display_path(self.root, target)}", kind="delete")

    def _syntax_check(self, path: Path, content: str) -> str:
        try:
            if path.suffix == ".py":
                compile(content, str(path), "exec")
            elif path.suffix == ".json":
                json.loads(content)
        except SyntaxError as exc:
            return f"{exc.__class__.__name__}: {exc}"
        except json.JSONDecodeError as exc:
            return f"JSONDecodeError: {exc}"
        return ""
