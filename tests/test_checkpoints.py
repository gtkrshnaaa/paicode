from pathlib import Path

from paicode.checkpoints import CheckpointStore
from paicode.cli import main
from paicode.core.stats import UsageStats
from paicode.tools.fs import FileTools


def test_write_and_edit_are_rewindable(project: Path, config_home: Path):
    tools = FileTools(project, UsageStats())
    tools.write("notes.txt", "one\n")
    tools.edit("notes.txt", "one", "two")
    assert (project / "notes.txt").read_text(encoding="utf-8") == "two\n"
    store = CheckpointStore(project)
    rows = store.list()
    assert rows
    checkpoint, restored = store.restore("latest")
    assert checkpoint is not None
    assert restored == ["notes.txt"]
    assert (project / "notes.txt").read_text(encoding="utf-8") == "one\n"


def test_delete_and_move_are_rewindable(project: Path, config_home: Path):
    tools = FileTools(project, UsageStats())
    tools.write("keep.txt", "body\n")
    tools.move("keep.txt", "moved.txt")
    assert not (project / "keep.txt").exists()
    assert (project / "moved.txt").is_file()
    store = CheckpointStore(project)
    store.restore("latest")
    assert (project / "keep.txt").read_text(encoding="utf-8") == "body\n"
    assert not (project / "moved.txt").exists()

    tools.delete("keep.txt")
    assert not (project / "keep.txt").exists()
    store.restore("latest")
    assert (project / "keep.txt").read_text(encoding="utf-8") == "body\n"


def test_rewind_cli_lists_and_restores(project: Path, config_home: Path, capsys):
    tools = FileTools(project, UsageStats())
    tools.write("cli.txt", "first\n")
    tools.write("cli.txt", "second\n")
    assert main(["--path", str(project), "rewind"]) == 0
    listing = capsys.readouterr().out
    assert "files=1" in listing
    assert main(["--path", str(project), "rewind", "latest"]) == 0
    output = capsys.readouterr().out
    assert "Restored" in output
    assert (project / "cli.txt").read_text(encoding="utf-8") == "first\n"
