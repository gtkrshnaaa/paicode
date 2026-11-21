import os
import sqlite3
from pathlib import Path

from paicode.db import Database
from paicode.providers.presets import PRESETS


def test_initialize_seeds_presets_and_secures_database(config_home: Path):
    database = Database()
    seeded = database.initialize()
    assert seeded[:3] == ["deepseek", "opencode", "openai"]
    assert len(seeded) == len(PRESETS)
    counts = database.counts()
    assert counts["provider_presets"] == len(PRESETS)
    assert oct(os.stat(database.path).st_mode & 0o777) == "0o600"

    database.initialize()
    assert database.counts()["provider_presets"] == len(PRESETS)


def test_reset_backs_up_and_creates_a_fresh_seeded_database(config_home: Path):
    database = Database()
    database.initialize()
    with database.connection() as conn:
        conn.execute(
            "INSERT INTO providers (name, base_url, model, models_url) VALUES ('demo', 'http://localhost/v1', '', '')"
        )
        conn.execute(
            "INSERT INTO sessions (id, workspace, created_at, last_opened_at, title, stats_json) "
            "VALUES ('s-demo', '/tmp', 'now', 'now', 'demo', '{}')"
        )

    result = database.reset()
    assert result["backup"] is not None
    assert result["backup"].exists()
    assert result["migrations"] == 1
    assert result["seeded"][:3] == ["deepseek", "opencode", "openai"]

    counts = database.counts()
    assert counts["providers"] == 0
    assert counts["sessions"] == 0
    assert counts["provider_presets"] == len(PRESETS)

    with sqlite3.connect(result["backup"]) as conn:
        assert conn.execute("SELECT base_url FROM providers WHERE name = 'demo'").fetchone()[0] == "http://localhost/v1"
