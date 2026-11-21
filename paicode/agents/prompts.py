import json
from pathlib import Path

from .contract import BuildContract, WorkUnit
from .findings import Finding
from .roles import AgentRole, role_for

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
CONTEXT_FILES = ("README.md", "PAICODE.md", "AGENTS.md", "pyproject.toml", "package.json", "setup.cfg")


def repo_snapshot(root: Path, limit: int = 16_000) -> str:
    lines = [f"Project root: {root}"]
    for name in CONTEXT_FILES:
        target = root / name
        if target.is_file():
            text = target.read_text(encoding="utf-8", errors="ignore")[:4_000]
            lines.extend([f"--- {name} ---", text, f"--- end {name} ---"])
    tree = []
    for path in sorted(root.rglob("*")):
        if len(tree) >= 250:
            tree.append("... tree truncated ...")
            break
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            tree.append(str(path.relative_to(root)))
    lines.extend(["--- file tree ---", *tree, "--- end file tree ---"])
    return "\n".join(lines)[:limit]


def proposal_prompt(role: AgentRole, request: str, context: str) -> str:
    return f"""You are Paicode agent {role.id}, {role.title}.
Role: {role.description}

The user requested:
{request}

Repository context:
{context}

This is the council proposal round. Do not write code. Analyze the request from your role.
Return only JSON with this shape:
{{
  "agent": {role.id},
  "role": "{role.title}",
  "understanding": "what the feature means from your role",
  "files": ["relative/path.py"],
  "interfaces": ["function/class/API/DOM/DB contract you need frozen"],
  "tests": ["test case that should exist"],
  "risks": ["risk or edge case"],
  "objections": ["conflict or ambiguity to resolve"],
  "owned_areas": ["area you can own"]
}}
Keep the response under 1200 words. Use relative paths only. Never include secrets."""


def synthesis_prompt(request: str, context: str, proposals: list[dict]) -> str:
    rendered = "\n\n".join(
        f"AGENT {item.get('agent', '?')}: {json.dumps(item, ensure_ascii=False)[:2500]}"
        for item in proposals
    )
    return f"""You are Paicode agent 1, the Lead Architect. Synthesize the council proposals into one frozen build contract.

User request:
{request}

Repository context:
{context}

Council proposals:
{rendered}

Return only JSON with this exact shape:
{{
  "feature": "short feature name",
  "acceptance": ["observable acceptance criterion"],
  "work_units": [
    {{
      "id": "wu-1",
      "title": "short unit title",
      "owner": 2,
      "files": ["relative/path.py"],
      "interfaces": "what this unit must export and consume",
      "notes": "implementation constraints"
    }}
  ],
  "shared_files": ["relative/path owned by the lead"],
  "interfaces": "canonical signatures, types, names, and imports",
  "api": "routes, methods, request/response shapes, errors",
  "database": "tables, columns, indexes, migrations",
  "ui": "routes, DOM tree, components, props, state, CSS tokens",
  "test_plan": ["test that must exist and what it proves"],
  "commands": {{"test": "command", "lint": "command", "build": "command"}},
  "non_goals": ["explicit non-goal"],
  "risks": ["risk and mitigation"]
}}

Rules:
- Owners must be agents 2 to 21.
- At most 20 work units.
- Every file has exactly one owner.
- No file appears in both work_units and shared_files.
- Group small related files into one work unit instead of exceeding 20 units.
- If the feature needs only a few files, leave most builders idle.
- Tests must map to acceptance criteria.
- Keep relative paths. No secrets. Return JSON only."""


def contract_review_prompt(role: AgentRole, request: str, contract: BuildContract) -> str:
    return f"""You are Paicode agent {role.id}, {role.title}.
Role: {role.description}

Review this frozen-candidate contract for the user request:
{request}

{contract.markdown()}

Return only JSON:
{{
  "agent": {role.id},
  "verdict": "approve|object",
  "required_changes": ["specific change needed"],
  "notes": "short note"
}}
Object only for a concrete correctness, ownership, interface, test, security, or feasibility problem. Do not object for style preference."""


def finalize_prompt(contract: BuildContract, reviews: list[dict]) -> str:
    rendered = "\n\n".join(
        f"AGENT {item.get('agent', '?')}: {json.dumps(item, ensure_ascii=False)[:1500]}"
        for item in reviews
    )
    return f"""You are Paicode agent 1, the Lead Architect. Resolve the contract reviews and return the final frozen contract.

Current contract:
{json.dumps(contract.to_dict(), ensure_ascii=False)}

Reviews:
{rendered}

Apply only concrete required changes. Return the same JSON shape as the current contract. Validate that owners are agents 2 to 21, work_units is at most 20, every file has one owner, and no file is both shared and owned."""


def builder_system_prompt(contract: BuildContract, units: list[WorkUnit], findings: list[Finding] | None = None) -> str:
    owner = units[0].owner
    owned = "\n".join(f"- {path}" for unit in units for path in unit.files)
    all_files = "\n".join(
        f"- {path} -> agent {owner}" for path, owner in sorted(contract.ownership().items())
    )
    unit_text = "\n".join(
        f"- {unit.id}: {unit.title}. Interfaces: {unit.interfaces or 'follow the contract'}. "
        f"Notes: {unit.notes or 'none'}. Files: {', '.join(unit.files)}"
        for unit in units
    )
    feedback = ""
    if findings:
        feedback = "\nRepair findings from agent 22:\n" + "\n".join(
            f"- [{item.severity}] {item.title} in {item.file or 'unknown'}: "
            f"expected {item.expected or '?'}, actual {item.actual or '?'}. "
            f"Fix: {item.fix or item.message or 'restore contract conformance'}"
            for item in findings
        )
    return f"""You are Paicode agent {owner}, {role_for(owner).title}, a builder in a parallel team.
You are working inside a frozen build contract. Other builders are working at the same time.

Contract:
{contract.markdown()}

Your work units:
{unit_text}

You own and may edit only these files:
{owned}

All file owners:
{all_files}

Rules:
- Use read, grep, and list to inspect.
- Use write and edit for source changes.
- Never edit a file you do not own.
- Do not wait for other builders. Code against the frozen interfaces.
- Run the narrowest useful test or syntax check for your units.
- If a dependency file is missing, report a blocker instead of editing it.
- Do not use shell redirection to create or modify source files.
- Do not commit or push unless explicitly asked.
- When done, call finish with JSON:
  {{"status":"done|blocked","summary":"what changed","files":["..."],"commands":["..."],"blockers":["..."]}}
{feedback}"""


def validator_system_prompt(contract: BuildContract) -> str:
    return f"""You are Paicode agent 22, the independent Validator. You are the release gate.

Contract:
{contract.markdown()}

You must validate the integrated workspace, not just one file.
Use read, grep, list, and bash. Do not modify production source files.
Run the contract commands, acceptance checks, ownership audit, and additional edge-case tests.
You may create temporary validation files only outside the project or under a temporary directory.

When done, call finish with JSON:
{{
  "ok": true,
  "summary": "validation result",
  "commands": ["command and result"],
  "findings": [
    {{
      "owner": 7,
      "severity": "critical|major|minor",
      "title": "short defect title",
      "file": "relative/path",
      "line": 0,
      "expected": "expected behavior",
      "actual": "actual behavior",
      "command": "reproduction command",
      "fix": "required fix",
      "message": "strict, direct accountability message to the owner"
    }}
  ]
}}

A finding must be reproducible. If all checks pass, return ok true and no findings.
The accountability message must be strict and demanding, but never contain slurs, personal abuse, or emojis."""
