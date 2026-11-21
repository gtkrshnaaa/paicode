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

MAX_TEXT_BYTES = 20_000_000

SYSTEM_BLOCKED_ROOTS = (
    "/proc",
    "/sys",
    "/dev",
    "/run",
    "/boot",
    "/root",
    "/var/lib",
    "/var/run",
    "/etc/ssl/private",
    "/etc/pki/private",
    "/etc/letsencrypt/archive",
    "/etc/NetworkManager/system-connections",
    "/etc/openvpn",
    "/etc/wireguard",
)

SYSTEM_BLOCKED_PARTS = {
    ".aws",
    ".bash_history",
    ".docker",
    ".git",
    ".git-credentials",
    ".gnupg",
    ".kube",
    ".netrc",
    ".npmrc",
    ".pai_brain",
    ".pai_history",
    ".password-store",
    ".pypirc",
    ".python_history",
    ".ssh",
    ".zsh_history",
    "Keychains",
    "keyrings",
}

SYSTEM_BLOCKED_RELATIVE = {
    ".config/BraveSoftware",
    ".config/chromium",
    ".config/gcloud",
    ".config/gh",
    ".config/google-chrome",
    ".config/microsoft-edge",
    ".config/opencode",
    ".config/paicode",
    ".local/share/keyrings",
    ".local/share/paicode",
    ".mozilla",
}

SYSTEM_BLOCKED_FILES = {
    "credentials",
    "gshadow",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets",
    "shadow",
    "sudoers",
}

SYSTEM_BLOCKED_SUFFIXES = {
    ".jks",
    ".kdbx",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
}


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


def system_path_block_reason(path: Path) -> str | None:
    resolved = Path(path).expanduser().resolve()
    for blocked_root in SYSTEM_BLOCKED_ROOTS:
        root_path = Path(blocked_root)
        if resolved == root_path or is_inside(root_path, resolved):
            return f"System path '{blocked_root}' is restricted."

    if any(part in SYSTEM_BLOCKED_PARTS for part in resolved.parts):
        return "Path contains a restricted credential or history component."

    home = Path.home().resolve()
    if is_inside(home, resolved):
        relative = resolved.relative_to(home).as_posix()
        for blocked_relative in SYSTEM_BLOCKED_RELATIVE:
            if relative == blocked_relative or relative.startswith(blocked_relative + "/"):
                return f"Path '{blocked_relative}' is restricted."

    name = resolved.name
    if name in SYSTEM_BLOCKED_FILES or name == ".env" or name.startswith(".env."):
        return f"File '{name}' is restricted."
    if name.startswith("ssh_host_") and name.endswith("_key"):
        return "SSH host private keys are restricted."
    if resolved.suffix.lower() in SYSTEM_BLOCKED_SUFFIXES:
        return f"Files with suffix '{resolved.suffix.lower()}' are restricted."
    return None


def resolve_system_path(raw: str | Path, cwd: Path, must_exist: bool = True) -> Path:
    if raw is None or str(raw).strip() == "":
        raise PathSecurityError("A path is required for exploration.")
    value = Path(str(raw)).expanduser()
    candidate = value if value.is_absolute() else Path(cwd) / value
    resolved = candidate.resolve()
    blocked = system_path_block_reason(resolved)
    if blocked:
        raise PathSecurityError(blocked)
    if must_exist and not resolved.exists():
        raise PathSecurityError(f"Path '{raw}' does not exist.")
    return resolved
