import json
import os
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from .core.errors import ConfigError
from .core.paths import config_dir, project_root


GLOBAL_SETTINGS = "settings.json"
PROJECT_SETTINGS = Path(".paicode") / "settings.json"


def state_dir() -> Path:
    override = os.getenv("PAICODE_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.getenv("XDG_STATE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".local" / "state") / "paicode"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"{path} must contain a JSON object.")
    return payload


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@dataclass(frozen=True)
class PermissionRule:
    action: str
    resource: str
    effect: str
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PermissionRule":
        effect = str(data.get("effect", "allow")).strip().lower()
        if effect not in {"allow", "ask", "deny"}:
            raise ConfigError(f"Invalid permission effect: {effect}")
        action = str(data.get("action", "*")).strip().lower() or "*"
        resource = str(data.get("resource", "*")).strip() or "*"
        return cls(action, resource, effect, str(data.get("note", "")).strip())


@dataclass(frozen=True)
class McpServer:
    name: str
    transport: str = "stdio"
    command: list[str] = field(default_factory=list)
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout: int = 30

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "McpServer":
        transport = str(data.get("transport", "stdio")).strip().lower()
        if transport not in {"stdio", "http"}:
            raise ConfigError(f"MCP server {name} has unsupported transport {transport}")
        command = data.get("command", [])
        if isinstance(command, str):
            command = [command]
        return cls(
            name=name,
            transport=transport,
            command=[str(item) for item in command],
            url=str(data.get("url", "")).strip(),
            headers={str(key): str(value) for key, value in data.get("headers", {}).items()},
            env={str(key): str(value) for key, value in data.get("env", {}).items()},
            enabled=bool(data.get("enabled", True)),
            timeout=max(1, int(data.get("timeout", 30) or 30)),
        )


@dataclass(frozen=True)
class Hook:
    event: str
    command: str
    timeout: int = 30
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Hook":
        event = str(data.get("event", "")).strip()
        command = str(data.get("command", "")).strip()
        if not event or not command:
            raise ConfigError("Each hook requires event and command.")
        return cls(event, command, max(1, int(data.get("timeout", 30) or 30)), bool(data.get("enabled", True)))


@dataclass(frozen=True)
class Budget:
    max_tokens: int = 0
    max_cost_usd: float = 0.0
    prompt_price_per_million: float = 0.0
    completion_price_per_million: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(
            max_tokens=max(0, int(data.get("max_tokens", 0) or 0)),
            max_cost_usd=max(0.0, float(data.get("max_cost_usd", 0.0) or 0.0)),
            prompt_price_per_million=max(0.0, float(data.get("prompt_price_per_million", 0.0) or 0.0)),
            completion_price_per_million=max(0.0, float(data.get("completion_price_per_million", 0.0) or 0.0)),
        )

    def cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * self.prompt_price_per_million
            + completion_tokens * self.completion_price_per_million
        ) / 1_000_000

    def exceeded(self, tokens: int, cost: float) -> str:
        if self.max_tokens and tokens > self.max_tokens:
            return f"Token budget exceeded: {tokens} > {self.max_tokens}"
        if self.max_cost_usd and cost > self.max_cost_usd:
            return f"Cost budget exceeded: ${cost:.4f} > ${self.max_cost_usd:.4f}"
        return ""


@dataclass
class Settings:
    permission_mode: str = "standard"
    permissions: list[PermissionRule] = field(default_factory=list)
    mcp_servers: dict[str, McpServer] = field(default_factory=dict)
    hooks: list[Hook] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    telemetry: bool = False
    compaction_threshold_chars: int = 0
    compaction_keep_last: int = 8
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        mode = str(data.get("permission_mode", "standard")).strip().lower()
        if mode not in {"standard", "strict", "trusted"}:
            raise ConfigError(f"Invalid permission_mode: {mode}")
        servers = {
            str(name): McpServer.from_dict(str(name), value)
            for name, value in data.get("mcp", {}).get("servers", {}).items()
        }
        hooks = [Hook.from_dict(item) for item in data.get("hooks", [])]
        plugins = [str(item) for item in data.get("plugins", []) if str(item).strip()]
        return cls(
            permission_mode=mode,
            permissions=[PermissionRule.from_dict(item) for item in data.get("permissions", [])],
            mcp_servers=servers,
            hooks=hooks,
            plugins=plugins,
            diagnostics=[str(item) for item in data.get("diagnostics", []) if str(item).strip()],
            budget=Budget.from_dict(data.get("budget", {})),
            telemetry=bool(data.get("telemetry", False)),
            compaction_threshold_chars=max(0, int(data.get("compaction_threshold_chars", 0) or 0)),
            compaction_keep_last=max(2, int(data.get("compaction_keep_last", 8) or 8)),
            raw=data,
        )


def load_settings(root: Path | str | None = None) -> Settings:
    project = Path(root).expanduser().resolve() if root else project_root()
    global_data = _read_json(config_dir() / GLOBAL_SETTINGS)
    project_data = _read_json(project / PROJECT_SETTINGS)
    return Settings.from_dict(_deep_merge(global_data, project_data))


def permission_effect(settings: Settings, action: str, resource: str) -> str:
    if settings.permission_mode == "trusted":
        return "allow"
    effect = "allow"
    for rule in settings.permissions:
        if fnmatch(action.lower(), rule.action) and fnmatch(resource, rule.resource):
            effect = rule.effect
    if settings.permission_mode == "strict" and action in {"shell", "write", "mcp"} and effect == "allow":
        return "ask"
    return effect
