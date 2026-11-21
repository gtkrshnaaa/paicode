import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..core.errors import ConfigError
from ..core.paths import config_file
from ..db import Database


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
    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.initialize()
        self.legacy_path = config_file()
        self._migrate_legacy_json()

    def _migrate_legacy_json(self) -> None:
        with self.db.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
        if count:
            return
        if self.legacy_path.exists():
            self._import_paicode_config()
            return
        self._import_google_credentials()

    def _import_google_credentials(self) -> None:
        legacy = Path.home() / ".config" / "pai-code" / "credentials"
        if not legacy.exists():
            return
        try:
            payload = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        keys = payload.get("keys", {}) if isinstance(payload, dict) else {}
        values = [str(value).strip() for value in keys.values() if str(value).strip()]
        if not values:
            return
        from .presets import get_preset

        preset = get_preset("google")
        base_url = preset.base_url if preset else "https://generativelanguage.googleapis.com/v1beta/openai/"
        with self.db.connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO providers (name, base_url, model, models_url) VALUES ('google', ?, '', '')",
                (base_url,),
            )
            for key in values:
                conn.execute(
                    "INSERT OR IGNORE INTO provider_keys (provider, api_key) VALUES ('google', ?)",
                    (key,),
                )
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('active_provider', 'google') "
                "ON CONFLICT(key) DO UPDATE SET value = 'google'"
            )
        target = legacy.with_name(
            f"{legacy.name}.migrated-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        try:
            legacy.replace(target)
        except OSError:
            pass

    def _import_paicode_config(self) -> None:
        try:
            payload = json.loads(self.legacy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            target = self.legacy_path.with_name(
                f"{self.legacy_path.name}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
            try:
                self.legacy_path.replace(target)
            except OSError:
                pass
            return
        providers = payload.get("providers", {}) if isinstance(payload, dict) else {}
        if not isinstance(providers, dict) or not providers:
            return
        with self.db.connection() as conn:
            for name, data in providers.items():
                if not isinstance(data, dict):
                    continue
                base_url = str(data.get("base_url", "")).strip()
                if not base_url:
                    continue
                provider_name = slug_name(name)
                conn.execute(
                    "INSERT OR IGNORE INTO providers (name, base_url, model, models_url) VALUES (?, ?, ?, ?)",
                    (
                        provider_name,
                        base_url,
                        str(data.get("model", "")).strip(),
                        str(data.get("models_url", "")).strip(),
                    ),
                )
                for key in data.get("api_keys", []):
                    key = str(key).strip()
                    if key:
                        conn.execute(
                            "INSERT OR IGNORE INTO provider_keys (provider, api_key) VALUES (?, ?)",
                            (provider_name, key),
                        )
                for index, model in enumerate(data.get("models", [])):
                    model = str(model).strip()
                    if model:
                        conn.execute(
                            "INSERT OR IGNORE INTO provider_models (provider, model, sort_order) VALUES (?, ?, ?)",
                            (provider_name, model, index),
                        )
            active = payload.get("active")
            if active:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('active_provider', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (slug_name(str(active)),),
                )
        target = self.legacy_path.with_name(
            f"{self.legacy_path.name}.migrated-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        try:
            self.legacy_path.replace(target)
        except OSError:
            pass

    def _provider(self, name: str) -> ProviderConfig | None:
        provider_name = slug_name(name)
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM providers WHERE name = ?", (provider_name,)).fetchone()
            if row is None:
                return None
            keys = [
                item["api_key"]
                for item in conn.execute(
                    "SELECT api_key FROM provider_keys WHERE provider = ? ORDER BY id",
                    (provider_name,),
                ).fetchall()
            ]
            models = [
                item["model"]
                for item in conn.execute(
                    "SELECT model FROM provider_models WHERE provider = ? ORDER BY sort_order, model",
                    (provider_name,),
                ).fetchall()
            ]
        return ProviderConfig(
            name=row["name"],
            base_url=row["base_url"],
            api_keys=keys,
            model=row["model"],
            models=models,
            models_url=row["models_url"],
        )

    def load(self) -> dict:
        providers = {provider.name: provider.to_dict() for provider in self.list()}
        active = self.active_name()
        return {"version": 2, "active": active, "providers": providers}

    def active_name(self) -> str | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'active_provider'"
            ).fetchone()
        return row["value"] if row else None

    def get(self, name: str) -> ProviderConfig | None:
        return self._provider(name)

    def active(self) -> ProviderConfig | None:
        name = self.active_name()
        return self.get(name) if name else None

    def list(self) -> list[ProviderConfig]:
        with self.db.connection() as conn:
            names = [
                row["name"]
                for row in conn.execute("SELECT name FROM providers ORDER BY name").fetchall()
            ]
        return [provider for name in names if (provider := self.get(name)) is not None]

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

        with self.db.connection() as conn:
            existing = conn.execute(
                "SELECT * FROM providers WHERE name = ?", (provider_name,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO providers (name, base_url, model, models_url) VALUES (?, ?, ?, ?)",
                    (provider_name, base_url, model or "", models_url or ""),
                )
            else:
                conn.execute(
                    "UPDATE providers SET base_url = ?, model = ?, models_url = ? WHERE name = ?",
                    (
                        base_url,
                        model if model is not None else existing["model"],
                        models_url if models_url is not None else existing["models_url"],
                        provider_name,
                    ),
                )
            if api_key:
                conn.execute(
                    "INSERT OR IGNORE INTO provider_keys (provider, api_key) VALUES (?, ?)",
                    (provider_name, api_key),
                )
            active = conn.execute(
                "SELECT value FROM settings WHERE key = 'active_provider'"
            ).fetchone()
            if active is None:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('active_provider', ?)",
                    (provider_name,),
                )
        return self.get(provider_name)

    def add_key(self, name: str, api_key: str) -> ProviderConfig:
        api_key = api_key.strip()
        if not api_key:
            raise ConfigError("API key is empty.")
        provider_name = slug_name(name)
        with self.db.connection() as conn:
            row = conn.execute("SELECT name FROM providers WHERE name = ?", (provider_name,)).fetchone()
            if row is None:
                raise ConfigError(f"Provider '{provider_name}' is not configured.")
            conn.execute(
                "INSERT OR IGNORE INTO provider_keys (provider, api_key) VALUES (?, ?)",
                (provider_name, api_key),
            )
        return self.get(provider_name)

    def set_model(self, name: str, model: str) -> ProviderConfig:
        model = model.strip()
        if not model:
            raise ConfigError("Model name is empty.")
        provider_name = slug_name(name)
        with self.db.connection() as conn:
            row = conn.execute("SELECT name FROM providers WHERE name = ?", (provider_name,)).fetchone()
            if row is None:
                raise ConfigError(f"Provider '{provider_name}' is not configured.")
            conn.execute("UPDATE providers SET model = ? WHERE name = ?", (model, provider_name))
        return self.get(provider_name)

    def set_models(self, name: str, models: list[str]) -> ProviderConfig:
        provider_name = slug_name(name)
        with self.db.connection() as conn:
            row = conn.execute("SELECT name FROM providers WHERE name = ?", (provider_name,)).fetchone()
            if row is None:
                raise ConfigError(f"Provider '{provider_name}' is not configured.")
            conn.execute("DELETE FROM provider_models WHERE provider = ?", (provider_name,))
            for index, model in enumerate(models):
                model = str(model).strip()
                if model:
                    conn.execute(
                        "INSERT OR IGNORE INTO provider_models (provider, model, sort_order) VALUES (?, ?, ?)",
                        (provider_name, model, index),
                    )
        return self.get(provider_name)

    def set_active(self, name: str) -> ProviderConfig:
        provider_name = slug_name(name)
        if self.get(provider_name) is None:
            raise ConfigError(f"Provider '{provider_name}' is not configured.")
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('active_provider', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (provider_name,),
            )
        return self.get(provider_name)

    def remove(self, name: str) -> None:
        provider_name = slug_name(name)
        with self.db.connection() as conn:
            conn.execute("DELETE FROM providers WHERE name = ?", (provider_name,))
            active = conn.execute(
                "SELECT value FROM settings WHERE key = 'active_provider'"
            ).fetchone()
            if active and active["value"] == provider_name:
                remaining = conn.execute("SELECT name FROM providers ORDER BY name LIMIT 1").fetchone()
                if remaining:
                    conn.execute(
                        "UPDATE settings SET value = ? WHERE key = 'active_provider'",
                        (remaining["name"],),
                    )
                else:
                    conn.execute("DELETE FROM settings WHERE key = 'active_provider'")

    def redacted(self) -> str:
        active = self.active_name()
        lines = [f"Database: {self.db.path}", f"Active: {active or 'none'}"]
        for provider in self.list():
            keys = ", ".join(provider.masked_keys()) or "none"
            lines.append(
                f"- {provider.name}: {provider.base_url} model={provider.model or 'unset'} keys={keys}"
            )
        return "\n".join(lines)

    def presets(self) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM provider_presets ORDER BY sort_order, name"
            ).fetchall()
        return [dict(row) for row in rows]
