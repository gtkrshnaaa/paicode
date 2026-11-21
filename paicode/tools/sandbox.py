import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600
OUTPUT_LIMIT = 200_000
OUTPUT_HEAD = 40_000
SANDBOX_CACHE_NAME = "paicode/sandbox"
OPTIONAL_TOOL_DIRS = (
    ".cargo/bin",
    ".rustup",
    ".bun",
    ".nvm",
    ".pyenv",
    ".local/bin",
    "go/bin",
)
DOCKER_SOCKET = Path("/var/run/docker.sock")
_PROBE_CACHE: dict[tuple[str, str], bool] = {}


def sandbox_mode() -> str:
    value = os.getenv("PAICODE_SHELL_SANDBOX", "auto").strip().lower()
    return value or "auto"


def sandbox_available() -> bool:
    mode = sandbox_mode()
    if mode in {"0", "off", "false", "direct", "none"}:
        return False
    bwrap = shutil.which("bwrap") or ""
    if not bwrap:
        return False
    key = (mode, bwrap)
    if key in _PROBE_CACHE:
        return _PROBE_CACHE[key]
    try:
        probe = subprocess.run(
            [
                "bwrap",
                "--die-with-parent",
                "--ro-bind",
                "/",
                "/",
                "--dev",
                "/dev",
                "--proc",
                "/proc",
                "--",
                "true",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        _PROBE_CACHE[key] = False
        return False
    _PROBE_CACHE[key] = probe.returncode == 0
    return _PROBE_CACHE[key]


def sandbox_cache_dir() -> Path:
    override = os.getenv("PAICODE_SANDBOX_CACHE")
    if override:
        base = Path(override).expanduser().resolve()
    else:
        cache_home = os.getenv("XDG_CACHE_HOME")
        root = Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
        base = (root / SANDBOX_CACHE_NAME).resolve()
    base.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)
    except OSError:
        pass
    return base


def _optional_binds() -> list[str]:
    args: list[str] = []
    home = Path.home()
    for relative in OPTIONAL_TOOL_DIRS:
        source = home / relative
        if source.exists():
            args.extend(["--ro-bind", str(source), str(source)])
    if _env_true("PAICODE_SANDBOX_DOCKER") and DOCKER_SOCKET.exists():
        args.extend(["--bind", str(DOCKER_SOCKET), str(DOCKER_SOCKET)])
    return args


def _env_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "on", "yes"}


def sandbox_command(
    root: Path,
    cwd: Path,
    command: str,
    cache: Path,
    read_only_workspace: bool = False,
) -> list[str]:
    args = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--cap-drop",
        "ALL",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/home",
        "--dir",
        "/tmp/home",
        "--dir",
        "/tmp/home/.config",
        "--dir",
        "/tmp/home/.local/share",
        "--dir",
        "/tmp/home/run",
        "--dir",
        "/tmp/paicode-cache",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--bind",
        str(cache),
        "/tmp/paicode-cache",
    ]
    if read_only_workspace:
        args.extend(["--overlay-src", str(root), "--tmp-overlay", str(root)])
    else:
        args.extend(["--bind", str(root), str(root)])
    args.extend([*_optional_binds(), "--chdir", str(cwd)])
    network = os.getenv("PAICODE_SANDBOX_NETWORK", "1").strip().lower()
    if network in {"0", "off", "false", "none"}:
        args.extend(["--unshare-net"])
    args.extend(["--", "bash", "-lc", command])
    return args
