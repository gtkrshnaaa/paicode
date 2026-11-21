from pathlib import Path

from ..rules.loader import RuleFile, render_rules
from ..rules.skills import SkillMeta, render_catalog
from ..rules.frontmatter import truncate_text

BASE_PROMPT = """You are Paicode, a terminal coding agent working inside a local project.

Operating rules:
1. Inspect before changing. Use list, glob, and grep to locate real files, then read before edit.
2. Prefer edit for surgical changes. Use write only for new files or deliberate full rewrites.
3. Never invent paths, APIs, configuration keys, or package versions.
4. Run tests or syntax checks after meaningful changes when a command is available.
5. Use skills when their description matches the task. Call the skill tool to load one.
6. Follow the PAICODE.md rules below. Project rules override global rules on conflicts.
7. Keep prose short. Do not use emojis or em dashes. Reply in the user's language.
8. Call finish with a concise summary when the task is complete or cannot proceed.

Tool contract:
- read, write, edit, list, glob, grep, mkdir, move, delete operate inside the project root only.
- bash runs an allowlisted command with no shell operators, no pipes, and no redirection.
- finish stops the turn. Always call it when you are done.
"""


def build_system_prompt(root: Path, rules: list[RuleFile], skills: list[SkillMeta]) -> str:
    rule_text = render_rules(rules)
    rule_text = truncate_text(rule_text, 100_000)
    catalog = truncate_text(render_catalog(skills), 8_000)
    return "\n".join(
        [
            BASE_PROMPT,
            f"Project root: {root}",
            f"Project name: {root.name}",
            f"Top-level entries: {', '.join(sorted(item.name for item in root.iterdir() if not item.name.startswith('.'))[:30])}",
            "--- GLOBAL AND PROJECT RULES ---",
            rule_text,
            "--- END RULES ---",
            "--- AVAILABLE SKILLS ---",
            catalog,
            "--- END SKILLS ---",
        ]
    )
