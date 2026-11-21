MAX_SESSION_MESSAGES = 60
MAX_MESSAGE_CHARS = 50_000
MAX_TOOL_CHARS = 20_000
MAX_TRANSCRIPT_ENTRIES = 400
MAX_DIFFS = 300
MAX_DIFF_CHARS = 1_000_000


def sanitize_messages(messages: list[dict]) -> list[dict]:
    cleaned = []
    for message in messages[-MAX_SESSION_MESSAGES:]:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in {"user", "assistant", "tool"}:
            continue
        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
                elif isinstance(part, dict) and part.get("type") == "image_url":
                    parts.append("[image attachment omitted from restored session]")
            content = "\n".join(parts)
        if isinstance(content, str):
            limit = MAX_TOOL_CHARS if role == "tool" else MAX_MESSAGE_CHARS
            content = content[:limit]
        item = {"role": role, "content": content}
        if message.get("tool_calls"):
            item["tool_calls"] = message["tool_calls"]
        if message.get("tool_call_id"):
            item["tool_call_id"] = message["tool_call_id"]
        cleaned.append(item)
    return cleaned


def sanitize_transcript(entries: list[dict]) -> list[dict]:
    cleaned = []
    for entry in entries[-MAX_TRANSCRIPT_ENTRIES:]:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        if kind in {"user", "system"}:
            cleaned.append({"kind": kind, "text": str(entry.get("text", ""))[: MAX_MESSAGE_CHARS]})
        elif kind == "assistant":
            cleaned.append({"kind": kind, "text": str(entry.get("text", ""))[: MAX_MESSAGE_CHARS]})
        elif kind == "tool":
            cleaned.append(
                {
                    "kind": "tool",
                    "name": str(entry.get("name", "")),
                    "status": str(entry.get("status", "")),
                    "detail": str(entry.get("detail", ""))[:500],
                }
            )
    return cleaned


def sanitize_diffs(diffs: list[dict]) -> list[dict]:
    cleaned = []
    total = 0
    for entry in diffs[-MAX_DIFFS:]:
        if not isinstance(entry, dict):
            continue
        diff = str(entry.get("diff", ""))
        if total + len(diff) > MAX_DIFF_CHARS:
            break
        total += len(diff)
        cleaned.append(
            {
                "path": str(entry.get("path", "")),
                "diff": diff,
                "created_at": str(entry.get("created_at", "")),
            }
        )
    return cleaned
