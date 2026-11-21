import json
import os
from pathlib import Path

from paicode.sessions import SessionStore


def test_legacy_json_sessions_migrate_to_database(config_home: Path):
    state = Path(os.environ["PAICODE_STATE_DIR"])
    legacy = state / "sessions"
    legacy.mkdir(parents=True)
    record = {
        "id": "s-legacy01",
        "workspace": "/tmp/legacy-workspace",
        "created_at": "2026-11-21T10:00:00+07:00",
        "last_opened_at": "2026-11-21T10:05:00+07:00",
        "title": "legacy",
    }
    (legacy / "index.json").write_text(json.dumps({"version": 1, "sessions": [record]}), encoding="utf-8")
    (legacy / "s-legacy01.json").write_text(
        json.dumps(
            {
                **record,
                "messages": [{"role": "user", "content": "legacy message"}],
                "transcript": [{"kind": "user", "text": "legacy message"}],
                "diffs": [{"path": "old.py", "diff": "+old", "created_at": "2026-11-21T10:02:00+07:00"}],
                "stats": {"total_tokens": 7},
            }
        ),
        encoding="utf-8",
    )

    store = SessionStore()
    loaded = store.get("s-legacy01")
    assert loaded is not None
    assert loaded.record.title == "legacy"
    assert loaded.transcript[0]["text"] == "legacy message"
    assert loaded.diffs[0]["path"] == "old.py"
    assert loaded.stats["total_tokens"] == 7
    assert not legacy.exists()
    assert list(state.glob("sessions.migrated-*"))
