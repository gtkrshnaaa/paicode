import os
import shlex
import subprocess
from pathlib import Path

from .types import ToolResult

ALLOWED = {
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "find",
    "rg",
    "grep",
    "pytest",
    "python",
    "python3",
    "git",
    "make",
    "npm",
    "pnpm",
    "bun",
    "node",
    "go",
    "cargo",
    "rustc",
    "gcc",
    "g++",
    "clang",
    "cmake",
}

GIT_READ_ONLY = {
    "status",
    "diff",
    "log",
    "show",
    "branch",
    "rev-parse",
    "ls-files",
    "grep",
    "blame",
    "remote",
}

PACKAGE_READ_ONLY = {"test", "run", "--version", "-v"}

SENSITIVE_ENV_PARTS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
SENSITIVE_ENV_PREFIXES = (
    "OPENAI_",
    "DEEPSEEK_",
    "ANTHROPIC_",
    "GOOGLE_",
    "GITHUB_",
    "GH_",
    "AWS_",
)


class ShellTools:
    def __init__(self, root: Path, stats, timeout: int = 30):
        self.root = root
        self.stats = stats
        self.default_timeout = timeout

    def _reject_unsafe_paths(self, args: list[str]) -> None:
        for arg in args:
            if arg.startswith("-"):
                if "=" in arg:
                    value = arg.split("=", 1)[1]
                    if value.startswith(("/", "~")) or ".." in Path(value).parts:
                        raise ValueError(f"Path argument '{value}' escapes the project.")
                continue
            if arg.startswith(("/", "~")) or ".." in Path(arg).parts:
                raise ValueError(f"Path argument '{arg}' escapes the project.")

    def _validate(self, args: list[str]) -> None:
        program = Path(args[0]).name
        if program not in ALLOWED:
            raise ValueError(f"Command '{program}' is not on the allowlist.")
        self._reject_unsafe_paths(args)
        if len(args) == 1:
            return

        sub = args[1]
        if program == "git" and sub not in GIT_READ_ONLY:
            raise ValueError(f"git {sub} is not allowed. Only read-only git commands are permitted.")
        if program in {"npm", "pnpm", "bun"} and sub not in PACKAGE_READ_ONLY:
            raise ValueError(f"{program} {sub} is not allowed.")
        if program == "make":
            targets = [arg for arg in args[1:] if not arg.startswith("-")]
            if not targets or any(target not in {"test", "lint", "build", "check", "fmt", "format"} for target in targets):
                raise ValueError("Only make test, lint, build, check, fmt, and format are allowed.")
        if program in {"python", "python3"}:
            if sub in {"-c", "-"}:
                raise ValueError("Inline Python evaluation is not allowed.")
            if sub == "-m":
                module = args[2] if len(args) > 2 else ""
                if module not in {"pytest", "unittest", "compileall"}:
                    raise ValueError(f"python -m {module} is not allowed.")
            if sub.startswith("-") and sub not in {"-V", "--version", "-m"}:
                raise ValueError(f"python flag {sub} is not allowed.")
        if program == "node" and sub in {"-e", "--eval", "-p", "--print"}:
            raise ValueError("Inline Node evaluation is not allowed.")
        if program == "find" and any(flag in {"-delete", "-exec", "-execdir", "-ok", "-okdir"} for flag in args):
            raise ValueError("find with destructive or exec flags is not allowed.")
        if program == "rg" and any(flag in {"--pre", "--pre-glob"} for flag in args):
            raise ValueError("rg preprocessors are not allowed.")
        if program == "go" and sub not in {"test", "build", "vet", "fmt", "version"}:
            raise ValueError(f"go {sub} is not allowed.")
        if program == "cargo" and sub not in {"test", "build", "check", "clippy", "fmt", "--version"}:
            raise ValueError(f"cargo {sub} is not allowed.")

    def _environment(self) -> dict:
        result = {}
        for key, value in os.environ.items():
            upper = key.upper()
            if any(part in upper for part in SENSITIVE_ENV_PARTS):
                continue
            if any(upper.startswith(prefix) for prefix in SENSITIVE_ENV_PREFIXES):
                continue
            result[key] = value
        return result

    def run(self, command: str, timeout: int = 0) -> ToolResult:
        if any(token in command for token in [";", "|", "&", ">", "<", "`", "$("]):
            raise ValueError("Shell operators are not allowed.")
        try:
            args = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f"Could not parse command: {exc}") from exc
        if not args:
            raise ValueError("Empty command.")
        self._validate(args)
        limit = min(max(int(timeout or self.default_timeout), 1), 120)
        try:
            completed = subprocess.run(
                args,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=limit,
                env=self._environment(),
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            self.stats.mark("command")
            raise ValueError(f"Command timed out after {limit}s.") from exc
        except FileNotFoundError as exc:
            raise ValueError(f"Command not found: {args[0]}") from exc

        self.stats.mark("command")
        output = f"$ {command}\nexit {completed.returncode}"
        if completed.stdout:
            output += f"\n--- STDOUT ---\n{completed.stdout}"
        if completed.stderr:
            output += f"\n--- STDERR ---\n{completed.stderr}"
        return ToolResult(ok=completed.returncode == 0, output=output.strip()[:200_000], kind="command")
