from pathlib import Path

from paicode.cli import _expand_session_args, main
from paicode.sessions import SessionStore


def test_session_lists_cli_outputs_complete_info(tmp_path: Path, config_home: Path, capsys):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SessionStore()
    created = store.create(workspace, title="cli-demo")
    code = main(["session-lists"])
    output = capsys.readouterr().out
    assert code == 0
    assert created.record.id in output
    assert str(workspace.resolve()) in output
    assert "CREATED" in output
    assert "LAST OPENED" in output
    assert "cli-demo" in output


def test_dynamic_session_flag_expands(tmp_path: Path, config_home: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SessionStore()
    created = store.create(workspace)
    assert _expand_session_args([f"--{created.record.id}"]) == [
        "--session",
        created.record.id,
    ]
    assert _expand_session_args(["--unknown"]) == ["--unknown"]


def test_reset_db_cli_reports_backup_and_seeded_presets(config_home: Path, capsys):
    code = main(["--reset-db"])
    output = capsys.readouterr().out
    assert code == 0
    assert "Paicode database reset" in output
    assert "Seeded:" in output
    assert "deepseek, opencode, openai" in output


def test_main_creates_a_new_session_for_current_workspace(
    tmp_path: Path, config_home: Path, monkeypatch
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    captured = {}

    class FakeApp:
        def __init__(self, root, provider_store, session_store, session):
            captured["root"] = Path(root)
            captured["session"] = session

        def run(self):
            return None

    monkeypatch.setattr("paicode.tui.app.PaiCodeApp", FakeApp)
    code = main([])
    assert code == 0
    assert captured["root"] == workspace.resolve()
    assert captured["session"].record.workspace == str(workspace.resolve())
    assert any(
        record.id == captured["session"].record.id for record in SessionStore().list()
    )


def test_main_opens_dynamic_session_workspace(
    tmp_path: Path, config_home: Path, monkeypatch
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = SessionStore()
    created = store.create(workspace, title="open-me")
    captured = {}

    class FakeApp:
        def __init__(self, root, provider_store, session_store, session):
            captured["root"] = Path(root)
            captured["session_id"] = session.record.id

        def run(self):
            return None

    monkeypatch.setattr("paicode.tui.app.PaiCodeApp", FakeApp)
    code = main([f"--{created.record.id}"])
    assert code == 0
    assert captured["root"] == workspace.resolve()
    assert captured["session_id"] == created.record.id
