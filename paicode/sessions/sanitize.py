MAX_SESSION_MESSAGES = 60
MAX_MESSAGE_CHARS = 50_000
MAX_TOOL_CHARS = 20_000
MAX_TRANSCRIPT_ENTRIES = 400
MAX_DIFFS = 300
MAX_DIFF_CHARS = 1_000_000


def _sanitize_content(message: dict) -> tuple[str, object]:
    role = message.get("role")
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
    return role, content


def sanitize_messages(messages: list[dict]) -> list[dict]:
    valid = []
    index = 0
    while index < len(messages):
        message = messages[index]
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant", "tool"}:
            index += 1
            continue
        if message.get("role") == "assistant" and message.get("tool_calls"):
            expected = {
                str(call.get("id", ""))
                for call in message["tool_calls"]
                if isinstance(call, dict)
            }
            lookahead = index + 1
            tool_messages = []
            while lookahead < len(messages) and messages[lookahead].get("role") == "tool":
                tool_messages.append(messages[lookahead])
                lookahead += 1
            received = {str(item.get("tool_call_id", "")) for item in tool_messages}
            if expected and not expected.issubset(received):
                index = lookahead
                continue
            role, content = _sanitize_content(message)
            valid.append({"role": role, "content": content, "tool_calls": message["tool_calls"]})
            for tool_message in tool_messages:
                role, content = _sanitize_content(tool_message)
                valid.append(
                    {
                        "role": role,
                        "content": content,
                        "tool_call_id": tool_message.get("tool_call_id", ""),
                    }
                )
            index = lookahead
            continue
        role, content = _sanitize_content(message)
        item = {"role": role, "content": content}
        if message.get("tool_call_id"):
            item["tool_call_id"] = message["tool_call_id"]
        valid.append(item)
        index += 1

    cleaned = valid[-MAX_SESSION_MESSAGES:]
    while cleaned and cleaned[0].get("role") == "tool":
        cleaned.pop(0)
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
