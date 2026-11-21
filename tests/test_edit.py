from pathlib import Path

import pytest

from paicode.tools.fs import FileTools


def test_edit_replaces_unique_match(project: Path, stats):
    target = project / "app.py"
    target.write_text("alpha = 1\nbeta = 2\ngamma = 3\n", encoding="utf-8")
    tools = FileTools(project, stats)
    result = tools.edit("app.py", "beta = 2", "beta = 20")
    assert result.ok
    assert "beta = 20" in target.read_text()
    assert "+beta = 20" in result.diff
    assert stats.files_edited == 1


def test_edit_rejects_ambiguous_match(project: Path, stats):
    (project / "app.py").write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    tools = FileTools(project, stats)
    with pytest.raises(ValueError, match="ambiguous"):
        tools.edit("app.py", "value = 1", "value = 2")


def test_edit_replace_all(project: Path, stats):
    (project / "app.py").write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    tools = FileTools(project, stats)
    result = tools.edit("app.py", "value = 1", "value = 2", replace_all=True)
    assert result.ok
    assert (project / "app.py").read_text().count("value = 2") == 2


def test_write_reports_python_syntax_failure(project: Path, stats):
    tools = FileTools(project, stats)
    result = tools.write("broken.py", "def broken(\n")
    assert result.ok
    assert "Syntax check failed" in result.output
    assert (project / "broken.py").exists()
    assert stats.files_created == 1


def test_edit_clears_stale_python_bytecode(project: Path, stats):
    target = project / "calculator.py"
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    cache = project / "__pycache__"
    cache.mkdir()
    compiled = cache / "calculator.cpython-314.pyc"
    compiled.write_bytes(b"stale")
    tools = FileTools(project, stats)
    result = tools.edit("calculator.py", "a - b", "a + b")
    assert result.ok
    assert not compiled.exists()


def test_write_existing_file_marks_edit(project: Path, stats):
    target = project / "README.md"
    tools = FileTools(project, stats)
    result = tools.write("README.md", "# Changed\n")
    assert result.ok
    assert "Updated README.md" in result.output
    assert target.read_text() == "# Changed\n"
    assert stats.files_edited == 1
