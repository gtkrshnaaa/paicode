import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from ..core.paths import display_path, resolve_in_root
from .sandbox import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    OUTPUT_HEAD,
    OUTPUT_LIMIT,
    sandbox_available,
    sandbox_cache_dir,
    sandbox_command,
    sandbox_mode,
)
from .shell_policy import guard_command, shell_environment
from .types import ToolResult


class ShellTools:
    def __init__(
        self,
        root: Path,
        stats,
        timeout: int = DEFAULT_TIMEOUT,
        stop_event=None,
        read_only_workspace: bool = False,
    ):
        self.root = root
        self.stats = stats
        self.default_timeout = timeout
        self.stop_event = stop_event
        self.read_only_workspace = read_only_workspace
        self.sandboxed = sandbox_available()
        if sandbox_mode() in {"required", "strict"} and not self.sandboxed:
            raise RuntimeError("PAICODE_SHELL_SANDBOX requires bubblewrap, but it is unavailable.")
        self.cache = sandbox_cache_dir() if self.sandboxed else None

    def run(self, command: str, timeout: int = 0, cwd: str = "") -> ToolResult:
        command = str(command or "").strip()
        if not command:
            raise ValueError("Empty command.")
        guard_command(command)
        cwd_path = resolve_in_root(self.root, cwd or ".", must_exist=True)
        if not cwd_path.is_dir():
            raise ValueError("Shell working directory is not a directory.")
        limit = min(max(int(timeout or self.default_timeout), 1), MAX_TIMEOUT)
        argv = (
            sandbox_command(
                self.root,
                cwd_path,
                command,
                self.cache,
                read_only_workspace=self.read_only_workspace,
            )
            if self.sandboxed
            else ["bash", "-lc", command]
        )

        self.stats.mark("command")
        with tempfile.TemporaryFile() as output:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=str(cwd_path),
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    env=shell_environment(self.sandboxed),
                    start_new_session=True,
                )
            except OSError as exc:
                raise ValueError(f"Could not start shell: {exc}") from exc

            timed_out = False
            stopped = False
            deadline = time.monotonic() + limit
            while process.poll() is None:
                if self.stop_event is not None and self.stop_event.is_set():
                    stopped = True
                    self._terminate(process)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    self._terminate(process)
                    break
                time.sleep(0.05)

            code = process.poll()
            body = self._read_output(output)

        if timed_out:
            status = f"exit timeout after {limit}s"
            ok = False
        elif stopped:
            status = "exit stopped by user"
            ok = False
        else:
            status = f"exit {code}"
            ok = code == 0
        header = f"$ {command}\ncwd: {display_path(self.root, cwd_path) or '.'}\n{status}"
        if body:
            header += f"\n--- OUTPUT ---\n{body}"
        return ToolResult(ok=ok, output=header[:OUTPUT_LIMIT], kind="command")

    def _terminate(self, process: subprocess.Popen) -> None:
        for sig, wait in ((signal.SIGTERM, 2), (signal.SIGKILL, 5)):
            try:
                os.killpg(process.pid, sig)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                process.wait(timeout=wait)
                return
            except subprocess.TimeoutExpired:
                continue

    @staticmethod
    def _read_output(handle) -> str:
        handle.flush()
        size = handle.seek(0, os.SEEK_END)
        handle.seek(0)
        if size <= OUTPUT_LIMIT:
            return handle.read().decode("utf-8", errors="replace")
        head = handle.read(OUTPUT_HEAD).decode("utf-8", errors="replace")
        handle.seek(max(0, size - (OUTPUT_LIMIT - OUTPUT_HEAD)))
        tail = handle.read().decode("utf-8", errors="replace")
        return f"{head}\n... [output truncated: {size} bytes total] ...\n{tail}"
