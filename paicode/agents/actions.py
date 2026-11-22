def tool_kind(name: str) -> str:
    mapping = {
        "read": "read",
        "write": "create",
        "edit": "edit",
        "delete": "delete",
        "list": "list",
        "glob": "glob",
        "grep": "search",
        "bash": "command",
        "skill": "skill",
        "explore": "explore",
        "mkdir": "mkdir",
        "move": "move",
        "finish": "finish",
    }
    return mapping.get((name or "").strip().lower(), (name or "action").strip().lower())


def tool_detail(arguments: dict) -> str:
    for key in ("command", "path", "pattern", "name", "source"):
        value = arguments.get(key)
        if value:
            return str(value).replace("\n", " ")[:120]
    return ""
