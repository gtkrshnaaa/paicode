from dataclasses import dataclass
from pathlib import Path

from ..core.paths import config_dir, is_inside
from .frontmatter import parse_frontmatter, truncate_text


@dataclass
class SkillMeta:
    name: str
    description: str
    path: Path
    scope: str


def _scan(base: Path, scope: str) -> list[SkillMeta]:
    if not base.is_dir():
        return []
    skills: list[SkillMeta] = []
    for skill_file in sorted(base.glob("*/SKILL.md")):
        try:
            text = skill_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta, _ = parse_frontmatter(text)
        name = (meta.get("name") or skill_file.parent.name).strip()
        description = (meta.get("description") or "").strip()
        skills.append(
            SkillMeta(
                name=name,
                description=description,
                path=skill_file.resolve(),
                scope=scope,
            )
        )
    return skills


def discover_skills(root: Path) -> list[SkillMeta]:
    global_skills = _scan(config_dir() / "skills", "global")
    project_skills = _scan(root / ".paicode" / "skills", "project")
    merged: dict[str, SkillMeta] = {}
    for skill in global_skills + project_skills:
        merged[skill.name.lower()] = skill
    return sorted(merged.values(), key=lambda skill: skill.name.lower())


def find_skill(skills: list[SkillMeta], name: str) -> SkillMeta | None:
    needle = name.strip().lower()
    for skill in skills:
        if skill.name.lower() == needle:
            return skill
    return None


def load_skill_text(skill: SkillMeta, limit: int = 30_000) -> str:
    if not is_inside(skill.path.parent, skill.path):
        raise ValueError(f"Skill path '{skill.path}' is outside its directory.")
    text = skill.path.read_text(encoding="utf-8", errors="ignore")
    return truncate_text(text, limit)


def render_catalog(skills: list[SkillMeta]) -> str:
    if not skills:
        return "No skills installed."
    lines = []
    for skill in skills:
        description = skill.description.replace("\n", " ").strip()
        if len(description) > 220:
            description = description[:217].rstrip() + "..."
        lines.append(f"- {skill.name} [{skill.scope}]: {description}")
    return "\n".join(lines)


def skill_path_summary(skills: list[SkillMeta]) -> str:
    if not skills:
        return "Skills: none installed"
    return "\n".join(f"- {skill.name} ({skill.scope}): {skill.path}" for skill in skills)
