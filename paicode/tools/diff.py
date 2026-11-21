import difflib


def unified_diff(old: str, new: str, path: str) -> tuple[str, int, int]:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
            n=3,
        )
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    return "\n".join(lines), added, removed


def looks_binary(sample: bytes) -> bool:
    return b"\x00" in sample[:4096]
