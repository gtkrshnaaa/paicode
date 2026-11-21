from pathlib import Path

from paicode.agents.contract import BuildContract, WorkUnit
from paicode.agents.roles import ROSTER
from paicode.agents.store import AgentStore
from paicode.tools.registry import ToolRegistry


def test_roster_has_twenty_two_agents():
    assert len(ROSTER) == 22
    assert ROSTER[0].id == 1
    assert ROSTER[0].is_builder is False
    assert ROSTER[1].id == 2 and ROSTER[1].is_builder
    assert ROSTER[-1].id == 22
    assert ROSTER[-1].is_builder is False


def test_contract_rejects_duplicate_owners_and_shared_collisions():
    contract = BuildContract(
        feature="duplicate",
        work_units=[
            WorkUnit("a", "a", 2, ["src/a.py"]),
            WorkUnit("b", "b", 3, ["src/a.py"]),
        ],
        shared_files=["src/a.py"],
    )
    errors = contract.validate()
    assert any("owners 2 and 3" in error for error in errors)
    assert any("both shared and builder-owned" in error for error in errors)


def test_contract_rejects_more_than_twenty_units():
    contract = BuildContract(
        feature="too many",
        work_units=[
            WorkUnit(f"u{index}", f"unit {index}", 2, [f"file{index}.txt"])
            for index in range(21)
        ],
    )
    assert "at most 20 work units are allowed" in contract.validate()


def test_registry_rejects_unowned_file_write(project: Path, stats):
    registry = ToolRegistry(project, stats, [], allowed_write_paths={project / "owned.txt"})
    result = registry.execute("write", {"path": "owned.txt", "content": "ok"})
    assert result.ok
    result = registry.execute("write", {"path": "unowned.txt", "content": "no"})
    assert not result.ok
    assert "does not own" in result.output
    assert not (project / "unowned.txt").exists()


def test_registry_read_only_blocks_edits(project: Path, stats):
    (project / "app.py").write_text("value = 1\n", encoding="utf-8")
    registry = ToolRegistry(project, stats, [], allowed_write_paths=set())
    result = registry.execute(
        "edit",
        {"path": "app.py", "old_string": "value = 1", "new_string": "value = 2"},
    )
    assert not result.ok
    assert "does not own" in result.output
    assert (project / "app.py").read_text(encoding="utf-8") == "value = 1\n"


def test_agent_store_persists_contract_and_findings(project: Path, config_home: Path):
    store = AgentStore()
    contract = BuildContract(
        feature="persist",
        work_units=[WorkUnit("a", "a", 2, ["a.txt"])],
    )
    contract_id = store.save_contract("s-persist", contract)
    assert contract_id
    assert store.latest_contract("s-persist").feature == "persist"
    run_id = store.create_run("s-persist", 2, "Frontend Shell", "build", model="fake")
    store.finish_run(run_id, "done", summary="ok", usage={"total_tokens": 5})
    assert store.agent_status("s-persist")[0]["total_tokens"] == 5
    validation_id = store.create_validation("s-persist", contract_id, 1)
    from paicode.agents.findings import Finding

    store.finish_validation(
        validation_id,
        "failed",
        "bug",
        [Finding(owner=2, severity="critical", title="bug", file="a.txt")],
    )
    findings = store.latest_findings("s-persist")
    assert findings[0]["owner"] == 2
    assert store.add_strike("s-persist", 2, "bug") == 1
    assert store.strike_count("s-persist", 2) == 1
