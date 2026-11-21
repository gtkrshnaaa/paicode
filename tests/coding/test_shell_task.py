from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_shell_script_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(registry, "notes/today.txt", "alpha\n")
    write_file(registry, "notes/tomorrow.txt", "beta\n")
    write_file(
        registry,
        "backup.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n\n"
        "destination=${1:-backup}\n"
        "mkdir -p \"$destination\"\n"
        "count=0\n"
        "for file in notes/*.txt; do\n"
        "  cp \"$file\" \"$destination/\"\n"
        "  count=$((count + 1))\n"
        "done\n"
        "printf 'backed up %s files\\n' \"$count\"\n",
    )
    output = run_command(registry, "chmod +x backup.sh && ./backup.sh archive")
    assert "backed up 2 files" in output
    assert (project / "archive/today.txt").is_file()
    assert (project / "archive/tomorrow.txt").is_file()


def test_json_pipeline_with_jq(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "config.json",
        '{"service":"api","ports":[8080,8443],"enabled":true}',
    )
    output = run_command(
        registry,
        "jq -r '.service' config.json && jq -e '.ports | length == 2' config.json",
    )
    assert "api" in output.splitlines()
