from pathlib import Path

import pytest

from paicode.core.errors import PathSecurityError
from paicode.core.paths import is_inside, resolve_in_root


def test_resolves_inside_project(project: Path):
    target = resolve_in_root(project, "README.md", must_exist=True)
    assert target == project / "README.md"


def test_rejects_parent_escape(project: Path):
    with pytest.raises(PathSecurityError):
        resolve_in_root(project, "../outside.txt")


def test_rejects_sibling_prefix_escape(project: Path):
    sibling = project.parent / f"{project.name}-evil"
    sibling.mkdir()
    with pytest.raises(PathSecurityError):
        resolve_in_root(project, f"../{sibling.name}/secret.txt")
    assert not is_inside(project, sibling)


def test_rejects_absolute_outside(project: Path):
    with pytest.raises(PathSecurityError):
        resolve_in_root(project, "/etc/passwd")


def test_rejects_sensitive_names(project: Path):
    (project / ".env").write_text("SECRET=1", encoding="utf-8")
    with pytest.raises(PathSecurityError):
        resolve_in_root(project, ".env")
    with pytest.raises(PathSecurityError):
        resolve_in_root(project, "nested/.git/config")
