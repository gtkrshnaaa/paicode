import subprocess
from pathlib import Path

from paicode.agents.contract import BuildContract, WorkUnit
from paicode.agents.validator import Validator
from paicode.core.stats import UsageStats
from paicode.providers.client import ProviderClient
from paicode.providers.store import ProviderConfig


def test_validator_flags_unowned_changed_file(project: Path, stats: UsageStats):
    (project / "owned.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "add", "owned.py"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=project, check=True)
    (project / "unowned.txt").write_text("outside contract\n", encoding="utf-8")
    provider = ProviderConfig(
        name="fake",
        base_url="http://127.0.0.1:9/v1",
        api_keys=["test"],
        model="fake",
    )
    validator = Validator(
        project,
        provider,
        ProviderClient(provider),
        stats,
        None,
        "audit-test",
        lambda event: None,
        None,
        "",
    )
    contract = BuildContract(
        feature="audit",
        work_units=[WorkUnit("wu-1", "owned", 2, ["owned.py"])],
    )
    _, _, findings = validator._precheck(contract)
    paths = {finding.file for finding in findings}
    assert "unowned.txt" in paths
    assert all(finding.owner == 1 for finding in findings if finding.file == "unowned.txt")
