import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.atomic import atomic_write_text, file_lock
from ..core.errors import ConfigError
from ..core.paths import config_file
from .presets import get_preset


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_keys: list[str] = field(default_factory=list)
    model: str = ""
    models: list[str] = field(default_factory=list)
    models_url: str = ""

    def active_key(self) -> str:
        return self.api_keys[0] if self.api_keys else ""

    def masked_keys(self) -> list[str]:
        return [mask_key(key) for key in self.api_keys]

    def to_dict(self) -> dict:
        return {
            "base_url": self.base_url,
            "api_keys": list(self.api_keys),
            "model": self.model,
            "models": list(self.models),
            "models_url": self.models_url,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "ProviderConfig":
        return cls(
            name=name,
            base_url=str(data.get("base_url", "")).strip(),
            api_keys=[str(key) for key in data.get("api_keys", []) if str(key).strip()],
            model=str(data.get("model", "")).strip(),
            models=[str(model) for model in data.get("models", []) if str(model).strip()],
            models_url=str(data.get("models_url", "")).strip(),
        )


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) < 10:
        return f"{key[:2]}...{key[-2:]}"
    return f"{key[:5]}...{key[-4:]}"


def slug_name(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return value or "provider"


class ProviderStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else config_file()

    def _default(self) -> dict:
        return {"version": 2, "active": None, "providers": {}}

    def _normalize(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return self._default()
        if "providers" not in data or not isinstance(data.get("providers"), dict):
            return self._default()
        data.setdefault("version", 2)
        data.setdefault("active", None)
        return data

    def _read(self) -> dict:
        if not self.path.exists():
            data = self._migrate_legacy()
            if data.get("providers"):
                self._write(data)
            return data
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return self._default()
        return self._normalize(data)

    def _write(self, data: dict) -> None:
        atomic_write_text(self.path, json.dumps(data, indent=2), mode=0o600)

    def _mutate(self, callback) -> dict:
        with file_lock(self.path):
            data = self._read()
            callback(data)
            self._write(data)
            return data

    def _migrate_legacy(self) -> dict:
        legacy = Path.home() / ".config" / "pai-code" / "credentials"
        data = self._default()
        if not legacy.exists():
            return data
        try:
            payload = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return data
        keys = payload.get("keys", {})
        if not isinstance(keys, dict) or not keys:
            return data
        preset = get_preset("google")
        values = [str(value) for value in keys.values() if str(value).strip()]
        if not values:
            return data
        data["providers"]["google"] = {
            "base_url": preset.base_url if preset else "",
            "api_keys": values,
            "model": preset.model if preset else "",
            "models": [],
            "models_url": "",
        }
        data["active"] = "google"
        return data

    def load(self) -> dict:
        return self._read()

    def get(self, name: str) -> ProviderConfig | None:
        data = self._read()
        payload = data.get("providers", {}).get(name)
        if not isinstance(payload, dict):
            return None
        return ProviderConfig.from_dict(name, payload)

    def active(self) -> ProviderConfig | None:
        data = self._read()
        name = data.get("active")
        if not name:
            return None
        return self.get(name)

    def list(self) -> list[ProviderConfig]:
        data = self._read()
        return [
            ProviderConfig.from_dict(name, payload)
            for name, payload in data.get("providers", {}).items()
            if isinstance(payload, dict)
        ]

    def upsert(
        self,
        name: str,
        base_url: str,
        api_key: str | None = None,
        model: str | None = None,
        models_url: str | None = None,
    ) -> ProviderConfig:
        provider_name = slug_name(name)
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url:
            raise ConfigError("Base URL is required.")
        if not base_url.startswith(("http://", "https://")):
            raise ConfigError("Base URL must start with http:// or https://")

        def apply(data: dict) -> None:
            providers = data.setdefault("providers", {})
            payload = providers.setdefault(
                provider_name,
                {"base_url": base_url, "api_keys": [], "model": "", "models": [], "models_url": ""},
            )
            payload["base_url"] = base_url
            if models_url is not None:
                payload["models_url"] = models_url.strip()
            if api_key:
                keys = payload.setdefault("api_keys", [])
                if api_key not in keys:
                    keys.append(api_key)
            if model:
                payload["model"] = model
            if not data.get("active"):
                data["active"] = provider_name

        data = self._mutate(apply)
        return ProviderConfig.from_dict(provider_name, data["providers"][provider_name])

    def add_key(self, name: str, api_key: str) -> ProviderConfig:
        api_key = api_key.strip()
        if not api_key:
            raise ConfigError("API key is empty.")

        def apply(data: dict) -> None:
            payload = data.get("providers", {}).get(name)
            if payload is None:
                raise ConfigError(f"Provider '{name}' is not configured.")
            keys = payload.setdefault("api_keys", [])
            if api_key not in keys:
                keys.append(api_key)

        data = self._mutate(apply)
        return ProviderConfig.from_dict(name, data["providers"][name])

    def set_model(self, name: str, model: str) -> ProviderConfig:
        model = model.strip()
        if not model:
            raise ConfigError("Model name is empty.")

        def apply(data: dict) -> None:
            payload = data.get("providers", {}).get(name)
            if payload is None:
                raise ConfigError(f"Provider '{name}' is not configured.")
            payload["model"] = model

        data = self._mutate(apply)
        return ProviderConfig.from_dict(name, data["providers"][name])

    def set_models(self, name: str, models: list[str]) -> ProviderConfig:
        def apply(data: dict) -> None:
            payload = data.get("providers", {}).get(name)
            if payload is None:
                raise ConfigError(f"Provider '{name}' is not configured.")
            payload["models"] = list(models)

        data = self._mutate(apply)
        return ProviderConfig.from_dict(name, data["providers"][name])

    def set_active(self, name: str) -> ProviderConfig:
        def apply(data: dict) -> None:
            if name not in data.get("providers", {}):
                raise ConfigError(f"Provider '{name}' is not configured.")
            data["active"] = name

        data = self._mutate(apply)
        return ProviderConfig.from_dict(name, data["providers"][name])

    def remove(self, name: str) -> None:
        def apply(data: dict) -> None:
            data.get("providers", {}).pop(name, None)
            if data.get("active") == name:
                remaining = data.get("providers", {})
                data["active"] = next(iter(remaining), None)

        self._mutate(apply)

    def redacted(self) -> str:
        data = self._read()
        active = data.get("active")
        lines = [f"Config: {self.path}", f"Active: {active or 'none'}"]
        for name, payload in data.get("providers", {}).items():
            provider = ProviderConfig.from_dict(name, payload)
            keys = ", ".join(provider.masked_keys()) or "none"
            lines.append(
                f"- {name}: {provider.base_url} model={provider.model or 'unset'} keys={keys}"
            )
        return "\n".join(lines)
