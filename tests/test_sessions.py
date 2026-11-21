from pathlib import Path

from paicode.core.stats import UsageStats
from paicode.sessions import SessionStore, format_sessions


def test_session_store_create_list_find_touch(tmp_path: Path, config_home: Path):
    workspace_a = tmp_path / "a"
    workspace_b = tmp_path / "b"
    workspace_a.mkdir()
    workspace_b.mkdir()
    store = SessionStore()

    first = store.create(workspace_a, title="first")
    second = store.create(workspace_b, title="second")
    assert first.record.id.startswith("s-")
    assert Path(first.record.workspace) == workspace_a.resolve()

    records = store.list()
    assert {record.id for record in records} == {first.record.id, second.record.id}
    assert store.find(first.record.id[:6]).id == first.record.id

    touched = store.touch(first.record.id)
    assert touched.record.last_opened_at >= touched.record.created_at

    table = format_sessions(store.list(), current_id=first.record.id)
    assert first.record.id in table
    assert str(workspace_a.resolve()) in table
    assert "* " in table
    assert "CREATED" in table
    assert "LAST OPENED" in table


def test_session_store_persists_transcript_diffs_messages_and_stats(tmp_path: Path, config_home: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SessionStore()
    data = store.create(workspace, title="demo")

    data.transcript = [
        {"kind": "user", "text": "hello"},
        {"kind": "tool", "name": "write", "status": "ok", "detail": "created app.py"},
        {"kind": "assistant", "text": "Done."},
    ]
    data.diffs = [
        {"path": "app.py", "diff": "--- a/app.py\n+++ b/app.py\n@@ -0,0 +1 @@\n+print('hi')", "created_at": "2026-11-21T10:00:00+07:00"}
    ]
    data.messages = [
        {"role": "user", "content": [{"type": "text", "text": "look"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]},
        {"role": "assistant", "content": "ok"},
    ]
    data.stats = UsageStats(prompt_tokens=10, completion_tokens=3, total_tokens=13).to_dict()
    store.save(data)

    loaded = store.get(data.record.id)
    assert loaded.transcript == data.transcript
    assert loaded.diffs[0]["path"] == "app.py"
    assert "image attachment omitted" in loaded.messages[0]["content"]
    assert loaded.stats["total_tokens"] == 13
