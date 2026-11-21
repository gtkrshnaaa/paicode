from dataclasses import dataclass
from pathlib import Path

from ..core.paths import config_dir
from .frontmatter import truncate_text


@dataclass
class RuleFile:
    path: Path
    scope: str
    content: str


def _read_rule(path: Path, scope: str, limit: int) -> RuleFile | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    text = text.strip()
    if not text:
        return None
    return RuleFile(path=path, scope=scope, content=truncate_text(text, limit))


def load_rules(root: Path, per_file_limit: int = 1_000_000) -> list[RuleFile]:
    global_dir = config_dir()
    rules: list[RuleFile] = []

    global_rule = _read_rule(global_dir / "PAICODE.md", "global", per_file_limit)
    if global_rule is None:
        global_rule = _read_rule(global_dir / "AGENTS.md", "global", per_file_limit)
    if global_rule:
        rules.append(global_rule)

    project_rule = _read_rule(root / "PAICODE.md", "project", per_file_limit)
    if project_rule is None:
        project_rule = _read_rule(root / "AGENTS.md", "project", per_file_limit)
    if project_rule:
        rules.append(project_rule)

    return rules


def render_rules(rules: list[RuleFile]) -> str:
    if not rules:
        return "No PAICODE.md rules are installed."
    blocks = []
    for rule in rules:
        blocks.append(
            f"--- {rule.scope.upper()} RULES: {rule.path} ---\n{rule.content.strip()}\n--- END {rule.scope.upper()} RULES ---"
        )
    return "\n\n".join(blocks)


def rule_summary(rules: list[RuleFile]) -> str:
    if not rules:
        return "Rules: none loaded"
    return "\n".join(f"- {rule.scope}: {rule.path} ({len(rule.content)} chars)" for rule in rules)
