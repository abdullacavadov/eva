from __future__ import annotations

from integrations.google.gmail import get_message, search_messages


def _format_message(message: dict[str, str], include_body: bool = False) -> str:
    lines = [
        f"ID: {message.get('id', '')}",
        f"Kimdən: {message.get('from', '')}",
        f"Kimə: {message.get('to', '')}",
        f"Mövzu: {message.get('subject', '')}",
        f"Tarix: {message.get('date', '')}",
    ]
    if include_body:
        lines.append(f"Məzmun:\n{message.get('body', '')}")
    else:
        lines.append(f"Qısa məzmun: {message.get('snippet', '')}")
    return "\n".join(lines)


def search_emails(query: str = "", limit: int = 10) -> str:
    messages = search_messages(query=query, limit=limit)
    if not messages:
        return "Heç bir email tapılmadı."
    return "\n\n".join(_format_message(message) for message in messages)


def read_email(message_id: str) -> str:
    return _format_message(get_message(message_id), include_body=True)
