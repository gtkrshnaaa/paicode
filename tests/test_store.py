import json
import os
import sqlite3
from pathlib import Path

from paicode.providers.store import ProviderStore


def test_upsert_and_reload(config_home: Path):
    store = ProviderStore()
    provider = store.upsert(
        "deepseek",
        "https://api.deepseek.com/v1",
        api_key="sk-test-123456789",
        model="deepseek-flash",
    )
    assert provider.name == "deepseek"
    assert provider.active_key() == "sk-test-123456789"
    assert store.active().model == "deepseek-flash"
    assert oct(os.stat(store.db.path).st_mode & 0o777) == "0o600"
    assert "sk-te...6789" in store.redacted()
    assert "sk-test-123456789" not in store.redacted()


def test_add_key_and_set_model(config_home: Path):
    store = ProviderStore()
    store.upsert("deepseek", "https://api.deepseek.com/v1", api_key="one", model="deepseek-flash")
    store.add_key("deepseek", "two")
    store.add_key("deepseek", "two")
    updated = store.set_model("deepseek", "deepseek-v4-pro")
    assert updated.api_keys == ["one", "two"]
    assert updated.model == "deepseek-v4-pro"


def test_database_contains_provider_rows(config_home: Path):
    store = ProviderStore()
    store.upsert("local", "http://127.0.0.1:9999/v1", api_key="key", model="model")
    with sqlite3.connect(store.db.path) as conn:
        assert conn.execute("SELECT base_url FROM providers WHERE name = 'local'").fetchone()[0] == "http://127.0.0.1:9999/v1"
        assert conn.execute("SELECT api_key FROM provider_keys WHERE provider = 'local'").fetchone()[0] == "key"
        assert conn.execute("SELECT value FROM settings WHERE key = 'active_provider'").fetchone()[0] == "local"


def test_presets_are_seeded(config_home: Path):
    store = ProviderStore()
    presets = store.presets()
    names = [preset["name"] for preset in presets]
    assert names[:3] == ["deepseek", "opencode", "openai"]
    assert "groq" in names
    assert "ollama" in names


def test_legacy_paicode_config_migrates_to_database(config_home: Path):
    config_home.mkdir(parents=True, exist_ok=True)
    (config_home / "config.json").write_text(
        json.dumps(
            {
                "version": 2,
                "active": "deepseek",
                "providers": {
                    "deepseek": {
                        "base_url": "https://api.deepseek.com/v1",
                        "api_keys": ["sk-legacy-key"],
                        "model": "deepseek-flash",
                        "models": ["deepseek-flash", "deepseek-v4-pro"],
                        "models_url": "",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    store = ProviderStore()
    provider = store.active()
    assert provider.name == "deepseek"
    assert provider.active_key() == "sk-legacy-key"
    assert provider.models == ["deepseek-flash", "deepseek-v4-pro"]
    assert not (config_home / "config.json").exists()
    assert list(config_home.glob("config.json.migrated-*"))


def test_legacy_google_credentials_migrate(tmp_path: Path, config_home: Path, monkeypatch):
    home = tmp_path / "home"
    legacy = home / ".config" / "pai-code" / "credentials"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"keys": {"main": "legacy-key-1"}, "default": "main"}), encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: home)
    store = ProviderStore()
    provider = store.active()
    assert provider.name == "google"
    assert provider.api_keys == ["legacy-key-1"]
    assert not legacy.exists()
