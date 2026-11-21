from pathlib import Path

from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderStore
from paicode.sessions import SessionStore
from paicode.tui.app import PaiCodeApp


async def test_switch_session_restores_workspace_transcript_diffs_and_stats(
    tmp_path: Path, config_home: Path
):
    workspace_a = tmp_path / "workspace-a"
    workspace_b = tmp_path / "workspace-b"
    workspace_a.mkdir()
    workspace_b.mkdir()
    store = SessionStore()
    first = store.create(workspace_a, title="first")
    second = store.create(workspace_b, title="second")
    second.transcript = [
        {"kind": "user", "text": "restored prompt"},
        {"kind": "assistant", "text": "restored answer"},
    ]
    second.diffs = [
        {
            "path": "demo.py",
            "diff": "--- a/demo.py\n+++ b/demo.py\n@@ -1 +1 @@\n-old\n+new",
            "created_at": "2026-11-21T10:00:00+07:00",
        }
    ]
    second.stats = UsageStats(total_tokens=42).to_dict()
    store.save(second)

    app = PaiCodeApp(workspace_a, ProviderStore(), session_store=store, session=first)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        assert app.root == workspace_a.resolve()
        assert app.session.record.id == first.record.id

        app._cmd_session(second.record.id)
        await pilot.pause()
        assert app.root == workspace_b.resolve()
        assert app.session.record.id == second.record.id
        assert any(
            entry.get("kind") == "user" and entry.get("text") == "restored prompt"
            for entry in app.chat.transcript
        )
        assert any(entry.get("kind") == "assistant" for entry in app.chat.transcript)
        assert app.session.diffs[0]["path"] == "demo.py"
        assert app.stats.total_tokens == 42

        app._cmd_sessions("")
        await pilot.pause()
        assert any(
            entry.get("kind") == "system" and second.record.id in entry.get("text", "")
            for entry in app.chat.transcript
        )


async def test_session_new_creates_a_new_session_in_current_workspace(
    tmp_path: Path, config_home: Path
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SessionStore()
    initial = store.create(workspace)
    app = PaiCodeApp(workspace, ProviderStore(), session_store=store, session=initial)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        original_id = app.session.record.id
        app._cmd_session("new")
        await pilot.pause()
        assert app.session.record.id != original_id
        assert Path(app.session.record.workspace) == workspace.resolve()
        assert app.root == workspace.resolve()
