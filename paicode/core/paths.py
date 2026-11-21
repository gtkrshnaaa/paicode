import os
from pathlib import Path

from .errors import PathSecurityError

SENSITIVE_NAMES = {
    ".env",
    ".git",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pai_brain",
    ".pai_history",
    ".ssh",
    ".venv",
    "__pycache__",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
    "node_modules",
    "venv",
}

EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pai_brain",
    ".pai_history",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}

MAX_TEXT_BYTES = 2_000_000


def project_root(start: Path | str | None = None) -> Path:
    override = os.getenv("PAICODE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(start or Path.cwd()).expanduser().resolve()


def config_dir() -> Path:
    override = os.getenv("PAICODE_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.getenv("XDG_CONFIG_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".config") / "paicode"


def config_file() -> Path:
    return config_dir() / "config.json"


def state_dir(root: Path) -> Path:
    return root / ".pai_brain"


def history_dir(root: Path) -> Path:
    return root / ".pai_history"


def is_inside(root: Path, candidate: Path) -> bool:
    try:
        return os.path.commonpath([str(root.resolve()), str(candidate.resolve())]) == str(root.resolve())
    except ValueError:
        return False


def resolve_in_root(root: Path, raw: str | Path, must_exist: bool = False) -> Path:
    if raw is None or str(raw).strip() == "":
        candidate = root
    else:
        value = Path(str(raw)).expanduser()
        candidate = value if value.is_absolute() else root / value

    resolved = candidate.resolve()
    root_resolved = root.resolve()

    if not is_inside(root_resolved, resolved):
        raise PathSecurityError(f"Path '{raw}' is outside the project root.")

    try:
        parts = resolved.relative_to(root_resolved).parts
    except ValueError as exc:
        raise PathSecurityError(f"Path '{raw}' is outside the project root.") from exc

    if any(part in SENSITIVE_NAMES for part in parts):
        raise PathSecurityError(f"Access to sensitive path '{raw}' is denied.")

    if must_exist and not resolved.exists():
        raise PathSecurityError(f"Path '{raw}' does not exist.")

    return resolved


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)
