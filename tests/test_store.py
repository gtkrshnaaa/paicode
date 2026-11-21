import json
import os
from pathlib import Path

from paicode.providers.store import ProviderStore


def test_upsert_and_reload(config_home: Path):
    store = ProviderStore()
    provider = store.upsert("deepseek", "https://api.deepseek.com/v1", api_key="sk-test-123456789", model="deepseek-flash")
    assert provider.name == "deepseek"
    assert provider.active_key() == "sk-test-123456789"
    assert store.active().model == "deepseek-flash"
    assert oct(os.stat(config_home / "config.json").st_mode & 0o777) == "0o600"
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


def test_config_is_valid_json(config_home: Path):
    store = ProviderStore()
    store.upsert("local", "http://127.0.0.1:9999/v1", api_key="key", model="model")
    payload = json.loads((config_home / "config.json").read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert payload["active"] == "local"
    assert list((config_home).glob("*.tmp")) == []


def test_legacy_migration(config_home: Path, tmp_path: Path, monkeypatch):
    legacy_dir = tmp_path / "home" / ".config" / "pai-code"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "credentials").write_text(
        json.dumps({"keys": {"main": "legacy-key-1"}, "default": "main"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    store = ProviderStore()
    provider = store.active()
    assert provider is not None
    assert provider.name == "google"
    assert provider.api_keys == ["legacy-key-1"]
