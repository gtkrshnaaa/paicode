from .models import SessionRecord, display_time


def format_sessions(records: list[SessionRecord], current_id: str | None = None) -> str:
    if not records:
        return "No sessions yet. Run pai to create one."
    rows = [
        (
            f"* {record.id}" if record.id == current_id else f"  {record.id}",
            record.workspace,
            display_time(record.created_at),
            display_time(record.last_opened_at),
            record.title,
        )
        for record in records
    ]
    headers = ("ID", "WORKSPACE", "CREATED", "LAST OPENED", "TITLE")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = [
        "  ".join(headers[index].ljust(widths[index]) for index in range(len(headers))),
        "  ".join("-" * width for width in widths),
    ]
    for row in rows:
        lines.append("  ".join(row[index].ljust(widths[index]) for index in range(len(headers))))
    return "\n".join(lines)


def format_session_detail(record: SessionRecord) -> str:
    return "\n".join(
        [
            f"ID: {record.id}",
            f"Workspace: {record.workspace}",
            f"Created: {display_time(record.created_at)}",
            f"Last opened: {display_time(record.last_opened_at)}",
            f"Title: {record.title}",
        ]
    )


def format_sessions_markdown(records: list[SessionRecord], current_id: str | None = None) -> str:
    if not records:
        return "## Sessions\n\nNo sessions yet. Run pai to create one."
    lines = ["## Sessions", ""]
    for record in records:
        marker = "*" if record.id == current_id else "-"
        lines.append(f"{marker} **`{record.id}`** · {record.title}")
        lines.append(f"  `{record.workspace}`")
        lines.append(
            f"  created {display_time(record.created_at)}  |  "
            f"last opened {display_time(record.last_opened_at)}"
        )
        lines.append("")
    return "\n".join(lines)


def format_session_detail_markdown(record: SessionRecord) -> str:
    return "\n".join(
        [
            "## Current Session",
            "",
            f"- **ID**: `{record.id}`",
            f"- **Workspace**: `{record.workspace}`",
            f"- **Created**: {display_time(record.created_at)}",
            f"- **Last opened**: {display_time(record.last_opened_at)}",
            f"- **Title**: {record.title}",
        ]
    )
