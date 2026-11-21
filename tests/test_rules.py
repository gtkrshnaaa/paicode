from pathlib import Path

from paicode.rules.loader import load_rules
from paicode.rules.skills import discover_skills, find_skill, load_skill_text


def test_load_global_and_project_rules(config_home: Path, project: Path):
    (config_home / "PAICODE.md").write_text("global rule", encoding="utf-8")
    (project / "PAICODE.md").write_text("project rule", encoding="utf-8")
    rules = load_rules(project)
    assert [rule.scope for rule in rules] == ["global", "project"]
    assert rules[0].content == "global rule"


def test_large_rule_file_is_not_truncated_at_fifty_thousand(config_home: Path, project: Path):
    payload = "x" * 55_000
    (project / "PAICODE.md").write_text(payload, encoding="utf-8")
    rules = load_rules(project)
    assert len(rules) == 1
    assert len(rules[0].content) == 55_000


def test_project_skill_overrides_global(config_home: Path, project: Path):
    global_skill = config_home / "skills" / "review" / "SKILL.md"
    global_skill.parent.mkdir(parents=True)
    global_skill.write_text("---\nname: review\ndescription: global\n---\nGlobal body\n", encoding="utf-8")
    project_skill = project / ".paicode" / "skills" / "review" / "SKILL.md"
    project_skill.parent.mkdir(parents=True)
    project_skill.write_text("---\nname: review\ndescription: project\n---\nProject body\n", encoding="utf-8")

    skills = discover_skills(project)
    assert len(skills) == 1
    assert skills[0].scope == "project"
    found = find_skill(skills, "REVIEW")
    assert found is not None
    assert "Project body" in load_skill_text(found)
