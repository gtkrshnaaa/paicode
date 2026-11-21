from pathlib import Path

from paicode.agent.prompts import build_system_prompt
from paicode.rules.loader import load_rules


def test_single_agent_prompt_keeps_large_global_rules(
    project: Path, config_home: Path
):
    marker = "END-OF-GLOBAL-RULES-MARKER"
    payload = "GLOBAL RULES START\n" + ("x" * 120_000) + "\n" + marker
    (config_home / "PAICODE.md").write_text(payload, encoding="utf-8")
    prompt = build_system_prompt(project, load_rules(project), [])
    assert "GLOBAL RULES START" in prompt
    assert marker in prompt


def test_global_rule_marker_is_present_with_project_rules(
    project: Path, config_home: Path
):
    (config_home / "PAICODE.md").write_text("GLOBAL-MARKER", encoding="utf-8")
    (project / "PAICODE.md").write_text("PROJECT-MARKER", encoding="utf-8")
    prompt = build_system_prompt(project, load_rules(project), [])
    assert "GLOBAL-MARKER" in prompt
    assert "PROJECT-MARKER" in prompt
