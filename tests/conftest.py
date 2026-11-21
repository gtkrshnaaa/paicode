from pathlib import Path

import pytest

from paicode.core.stats import UsageStats


@pytest.fixture(autouse=True)
def sandbox_cache(tmp_path: Path, monkeypatch) -> Path:
    cache = tmp_path / "sandbox-cache"
    monkeypatch.setenv("PAICODE_SANDBOX_CACHE", str(cache))
    return cache


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    return root


@pytest.fixture
def stats() -> UsageStats:
    return UsageStats()


@pytest.fixture
def config_home(tmp_path: Path, monkeypatch) -> Path:
    config = tmp_path / "config"
    config.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    state = tmp_path / "state"
    monkeypatch.setenv("PAICODE_CONFIG_DIR", str(config))
    monkeypatch.setenv("PAICODE_STATE_DIR", str(state))
    monkeypatch.setattr(Path, "home", lambda: home)
    return config
