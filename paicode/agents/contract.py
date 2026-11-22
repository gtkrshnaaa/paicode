from dataclasses import dataclass, field

from .json_utils import normalize_path
from .roles import BUILDER_IDS, role_for


@dataclass
class WorkUnit:
    id: str
    title: str
    owner: int
    files: list[str] = field(default_factory=list)
    interfaces: str = ""
    notes: str = ""
    depends_on: list[str] = field(default_factory=list)
    integration_order: int = 0
    integration_note: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "owner": self.owner,
            "files": list(self.files),
            "interfaces": self.interfaces,
            "notes": self.notes,
            "depends_on": list(self.depends_on),
            "integration_order": self.integration_order,
            "integration_note": self.integration_note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkUnit":
        return cls(
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            owner=int(data.get("owner", 0) or 0),
            files=[str(item).strip() for item in data.get("files", []) if str(item).strip()],
            interfaces=str(data.get("interfaces", "")).strip(),
            notes=str(data.get("notes", "")).strip(),
            depends_on=[str(item).strip() for item in data.get("depends_on", []) if str(item).strip()],
            integration_order=int(data.get("integration_order", 0) or 0),
            integration_note=str(data.get("integration_note", "")).strip(),
        )


@dataclass
class BuildContract:
    feature: str
    acceptance: list[str] = field(default_factory=list)
    work_units: list[WorkUnit] = field(default_factory=list)
    shared_files: list[str] = field(default_factory=list)
    interfaces: str = ""
    api: str = ""
    database: str = ""
    ui: str = ""
    test_plan: list[str] = field(default_factory=list)
    commands: dict[str, str] = field(default_factory=dict)
    non_goals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "acceptance": list(self.acceptance),
            "work_units": [unit.to_dict() for unit in self.work_units],
            "shared_files": list(self.shared_files),
            "interfaces": self.interfaces,
            "api": self.api,
            "database": self.database,
            "ui": self.ui,
            "test_plan": list(self.test_plan),
            "commands": dict(self.commands),
            "non_goals": list(self.non_goals),
            "risks": list(self.risks),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildContract":
        commands = data.get("commands", {})
        return cls(
            feature=str(data.get("feature", "")).strip(),
            acceptance=[str(item).strip() for item in data.get("acceptance", []) if str(item).strip()],
            work_units=[
                WorkUnit.from_dict(item)
                for item in data.get("work_units", [])
                if isinstance(item, dict)
            ],
            shared_files=[str(item).strip() for item in data.get("shared_files", []) if str(item).strip()],
            interfaces=str(data.get("interfaces", "")).strip(),
            api=str(data.get("api", "")).strip(),
            database=str(data.get("database", "")).strip(),
            ui=str(data.get("ui", "")).strip(),
            test_plan=[str(item).strip() for item in data.get("test_plan", []) if str(item).strip()],
            commands={str(key): str(value) for key, value in commands.items()} if isinstance(commands, dict) else {},
            non_goals=[str(item).strip() for item in data.get("non_goals", []) if str(item).strip()],
            risks=[str(item).strip() for item in data.get("risks", []) if str(item).strip()],
        )

    def ownership(self) -> dict[str, int]:
        owners: dict[str, int] = {}
        for unit in self.work_units:
            for path in unit.files:
                owners[path] = unit.owner
        return owners

    def builder_units(self) -> dict[int, list[WorkUnit]]:
        grouped: dict[int, list[WorkUnit]] = {}
        for unit in self.work_units:
            grouped.setdefault(unit.owner, []).append(unit)
        return grouped

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.feature:
            errors.append("feature is required")
        if not self.work_units:
            errors.append("at least one work unit is required")
        if len(self.work_units) > 20:
            errors.append("at most 20 work units are allowed")
        seen: dict[str, int] = {}
        owners: dict[int, str] = {}
        for unit in self.work_units:
            if not unit.id:
                errors.append("every work unit needs an id")
            if not unit.title:
                errors.append(f"work unit {unit.id or '?'} needs a title")
            if unit.owner not in BUILDER_IDS:
                errors.append(f"work unit {unit.id or '?'} has invalid owner {unit.owner}")
            elif unit.owner in owners:
                errors.append(
                    f"builder {unit.owner} owns both {owners[unit.owner]} and {unit.id or '?'}; "
                    "one builder must own exactly one work unit"
                )
            else:
                owners[unit.owner] = unit.id
            if not unit.files:
                errors.append(f"work unit {unit.id or '?'} needs at least one file")
            for path in unit.files:
                normalized = normalize_path(path)
                if not normalized:
                    errors.append(f"work unit {unit.id or '?'} has an invalid path")
                    continue
                if normalized in self.shared_files:
                    errors.append(f"{normalized} is both shared and builder-owned")
                if normalized in seen:
                    errors.append(f"{normalized} has owners {seen[normalized]} and {unit.owner}")
                seen[normalized] = unit.owner
        unit_ids = {unit.id for unit in self.work_units}
        for unit in self.work_units:
            for dependency in unit.depends_on:
                if dependency not in unit_ids:
                    errors.append(f"work unit {unit.id or '?'} depends on unknown unit {dependency}")
                if dependency == unit.id:
                    errors.append(f"work unit {unit.id or '?'} cannot depend on itself")
        for path in self.shared_files:
            normalized = normalize_path(path)
            if not normalized:
                errors.append("shared file path is invalid")
            elif normalized in seen:
                errors.append(f"shared file {normalized} is also builder-owned")
        return errors

    def markdown(self) -> str:
        lines = [
            f"# Build Contract: {self.feature}",
            "",
            "## Acceptance Criteria",
            *[f"- {item}" for item in self.acceptance],
            "",
            "## Work Units",
        ]
        for unit in self.work_units:
            lines.append(f"### {unit.id}: {unit.title}")
            lines.append(f"- Owner: agent {unit.owner} ({role_for(unit.owner).title})")
            lines.append("- Files:")
            lines.extend(f"  - `{path}`" for path in unit.files)
            if unit.interfaces:
                lines.append(f"- Interfaces: {unit.interfaces}")
            if unit.notes:
                lines.append(f"- Notes: {unit.notes}")
            if unit.depends_on:
                lines.append(f"- Depends on: {', '.join(unit.depends_on)}")
            if unit.integration_order:
                lines.append(f"- Integration order: {unit.integration_order}")
            if unit.integration_note:
                lines.append(f"- Integration note: {unit.integration_note}")
            lines.append("")
        if self.shared_files:
            lines.extend(["## Shared Files", *[f"- `{path}`" for path in self.shared_files], ""])
        for title, content in [
            ("Interfaces", self.interfaces),
            ("API", self.api),
            ("Database", self.database),
            ("UI", self.ui),
        ]:
            if content:
                lines.extend([f"## {title}", content, ""])
        if self.test_plan:
            lines.extend(["## Test Plan", *[f"- {item}" for item in self.test_plan], ""])
        if self.commands:
            lines.append("## Commands")
            lines.extend(f"- `{name}`: `{command}`" for name, command in self.commands.items())
            lines.append("")
        if self.non_goals:
            lines.extend(["## Non Goals", *[f"- {item}" for item in self.non_goals], ""])
        if self.risks:
            lines.extend(["## Risks", *[f"- {item}" for item in self.risks], ""])
        return "\n".join(lines).strip()
