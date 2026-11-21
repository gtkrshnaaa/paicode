import os
import re

SECRET_ENV_PARTS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
SECRET_ENV_PREFIXES = (
    "OPENAI_",
    "DEEPSEEK_",
    "ANTHROPIC_",
    "GOOGLE_",
    "GITHUB_",
    "GH_",
    "AWS_",
    "AZURE_",
    "GROQ_",
    "MISTRAL_",
    "OPENROUTER_",
)
BLOCKED_ENV = {
    "BASH_ENV",
    "ENV",
    "GIT_ASKPASS",
    "GPG_AGENT_INFO",
    "LD_PRELOAD",
    "PYTHONSTARTUP",
    "SSH_ASKPASS",
    "SSH_AUTH_SOCK",
}
DANGEROUS = (
    (re.compile(r"(^|[\s;&|])sudo(\s|$)"), "sudo is not allowed."),
    (re.compile(r"(^|[\s;&|])(su|doas)(\s|$)"), "Privilege escalation is not allowed."),
    (re.compile(r"\bmkfs(\.\w+)?\b"), "Filesystem creation is not allowed."),
    (re.compile(r"\bdd\b[^\n]*\bof=/dev/"), "Raw device writes are not allowed."),
    (
        re.compile(r"(^|[\s;&|])(shutdown|reboot|poweroff|halt)(\s|$)"),
        "Host power commands are not allowed.",
    ),
    (
        re.compile(r"\bsystemctl\s+(poweroff|reboot|halt|kexec|suspend|hibernate)\b"),
        "Host power commands are not allowed.",
    ),
    (
        re.compile(r"\bchmod\s+-R\s+777\s+/(?:\s|$)"),
        "Recursive root permission changes are not allowed.",
    ),
    (
        re.compile(r"\bchown\s+-R\s+\S+\s+/(?:\s|$)"),
        "Recursive root ownership changes are not allowed.",
    ),
    (
        re.compile(r"\brm\s+(-[A-Za-z]*[rR][A-Za-z]*\s+)+/(?:\s|$|\*)"),
        "Deleting the filesystem root is not allowed.",
    ),
    (
        re.compile(r"\brm\s+(-[A-Za-z]*[rR][A-Za-z]*\s+)+(~|\$HOME)(?:\s|$|\*)"),
        "Deleting the home directory is not allowed.",
    ),
    (re.compile(r"\bkill\s+-9\s+-1\b"), "Killing every process is not allowed."),
    (
        re.compile(r"\bdocker\b[^\n]*--privileged\b"),
        "Privileged containers are not allowed.",
    ),
    (
        re.compile(r"\b(npm\s+publish|cargo\s+publish|twine\s+upload)\b"),
        "Package publishing is not allowed.",
    ),
)
FORK_BOMB = (":(){", "|:&")
CACHE_DIR = "/tmp/paicode-cache"


def guard_command(command: str) -> None:
    lowered = " ".join(command.split())
    for pattern, message in DANGEROUS:
        if pattern.search(lowered):
            raise ValueError(message)
    if all(token in lowered.replace(" ", "") for token in FORK_BOMB):
        raise ValueError("Fork bombs are not allowed.")


def shell_environment(sandboxed: bool) -> dict[str, str]:
    result = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper in BLOCKED_ENV:
            continue
        if any(part in upper for part in SECRET_ENV_PARTS):
            continue
        if any(upper.startswith(prefix) for prefix in SECRET_ENV_PREFIXES):
            continue
        result[key] = value

    result.update(
        {
            "PAGER": "cat",
            "SYSTEMD_PAGER": "cat",
            "GIT_PAGER": "cat",
            "MANPAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "DEBIAN_FRONTEND": "noninteractive",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_COLOR": "1",
        }
    )
    if sandboxed:
        result.update(
            {
                "HOME": "/tmp/home",
                "XDG_CACHE_HOME": CACHE_DIR,
                "XDG_CONFIG_HOME": "/tmp/home/.config",
                "XDG_DATA_HOME": "/tmp/home/.local/share",
                "PIP_CACHE_DIR": f"{CACHE_DIR}/pip",
                "npm_config_cache": f"{CACHE_DIR}/npm",
                "NPM_CONFIG_CACHE": f"{CACHE_DIR}/npm",
                "BUN_INSTALL_CACHE_DIR": f"{CACHE_DIR}/bun",
                "CARGO_HOME": f"{CACHE_DIR}/cargo",
                "GOCACHE": f"{CACHE_DIR}/go-build",
                "GOMODCACHE": f"{CACHE_DIR}/go-mod",
                "UV_CACHE_DIR": f"{CACHE_DIR}/uv",
                "YARN_CACHE_FOLDER": f"{CACHE_DIR}/yarn",
                "GRADLE_USER_HOME": f"{CACHE_DIR}/gradle",
            }
        )
    return result
