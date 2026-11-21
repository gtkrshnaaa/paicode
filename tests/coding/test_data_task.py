import json
from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_toml_and_csv_data_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "pyproject.toml",
        "[project]\nname = \"sales-report\"\nversion = \"1.0.0\"\n",
    )
    write_file(
        registry,
        "data/sales.csv",
        "region,amount\nnorth,120\nsouth,80\nnorth,50\n",
    )
    write_file(
        registry,
        "report.py",
        "import csv\n"
        "import json\n"
        "import tomllib\n\n"
        "project = tomllib.load(open('pyproject.toml', 'rb'))['project']\n"
        "totals = {}\n"
        "with open('data/sales.csv', newline='') as handle:\n"
        "    for row in csv.DictReader(handle):\n"
        "        totals[row['region']] = totals.get(row['region'], 0) + int(row['amount'])\n"
        "print(json.dumps({'project': project['name'], 'totals': totals}, sort_keys=True))\n",
    )
    output = run_command(registry, "python3 report.py")
    payload = json.loads(output.split("--- OUTPUT ---", 1)[-1].strip())
    assert payload == {"project": "sales-report", "totals": {"north": 170, "south": 80}}
