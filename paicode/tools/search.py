import fnmatch
import glob as glob_module
import os
import re
from pathlib import Path

from ..core.paths import EXCLUDED_DIRS, MAX_TEXT_BYTES, SENSITIVE_NAMES, display_path, is_inside, resolve_in_root
from .diff import looks_binary
from .types import ToolResult


class SearchTools:
    def __init__(self, root: Path, stats):
        self.root = root
        self.stats = stats

    def glob(self, pattern: str) -> ToolResult:
        if not pattern or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ValueError("Glob pattern must be project-relative and must not contain '..'.")
        matches = []
        for raw in glob_module.glob(str(self.root / pattern), recursive=True):
            candidate = Path(raw)
            if not is_inside(self.root, candidate):
                continue
            relative = candidate.relative_to(self.root.resolve())
            if any(part in EXCLUDED_DIRS or part in SENSITIVE_NAMES for part in relative.parts):
                continue
            matches.append(str(relative) + ("/" if candidate.is_dir() else ""))
            if len(matches) >= 5_000:
                matches.append("... [truncated at 5,000 matches]")
                break
        output = "\n".join(sorted(matches)) if matches else f"No matches for '{pattern}'."
        return ToolResult(ok=True, output=output, kind="glob")

    def grep(self, pattern: str, path: str = ".", include: str | None = None) -> ToolResult:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regular expression: {exc}") from exc
        base = resolve_in_root(self.root, path or ".", must_exist=True)
        if base.is_file():
            files = [base]
        else:
            files = []
            for current, dirs, names in os.walk(base):
                dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS and name not in SENSITIVE_NAMES]
                for name in names:
                    if name in SENSITIVE_NAMES:
                        continue
                    if include and not fnmatch.fnmatch(name, include):
                        continue
                    files.append(Path(current) / name)

        results = []
        for file_path in files:
            if not is_inside(self.root, file_path) or not file_path.is_file():
                continue
            try:
                if file_path.stat().st_size > MAX_TEXT_BYTES:
                    continue
                raw = file_path.read_bytes()
                if looks_binary(raw):
                    continue
                text = raw.decode("utf-8", errors="ignore")
            except OSError:
                continue
            relative = display_path(self.root, file_path)
            for number, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    results.append(f"{relative}:{number}:{line.strip()[:300]}")
                    if len(results) >= 5_000:
                        results.append("... [truncated at 5,000 matches]")
                        return ToolResult(ok=True, output="\n".join(results), kind="grep")

        if not results:
            return ToolResult(ok=True, output=f"No matches for '{pattern}' in '{path}'.", kind="grep")
        return ToolResult(ok=True, output="\n".join(results), kind="grep")
