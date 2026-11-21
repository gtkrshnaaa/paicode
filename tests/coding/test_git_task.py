from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_git_branch_and_commit_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(registry, "app.py", "VERSION = '1.0.0'\n")
    run_command(registry, "git init -q")
    run_command(registry, "git config user.name Matrix")
    run_command(registry, "git config user.email matrix@example.com")
    run_command(registry, "git add app.py README.md")
    run_command(registry, "git commit -q -m 'initial'")
    run_command(registry, "git switch -q -c feature/version-bump")

    result = registry.execute(
        "edit",
        {
            "path": "app.py",
            "old_string": "VERSION = '1.0.0'",
            "new_string": "VERSION = '1.1.0'",
        },
    )
    assert result.ok, result.output
    run_command(registry, "git add app.py")
    run_command(registry, "git commit -q -m 'bump version'")
    output = run_command(registry, "git log --oneline --all")
    assert "initial" in output
    assert "bump version" in output
    status = run_command(registry, "git status --short")
    assert "app.py" not in status
