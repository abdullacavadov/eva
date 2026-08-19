from __future__ import annotations

from integrations.google.gmail import get_message, search_messages
from core.results import empty, error, success


def _structured_message(message: dict[str, str], include_body: bool = False) -> dict:
    return {
        "id": f"email:{message.get('id', '')}",
        "gmail_message_id": message.get("id", ""),
        "thread_id": message.get("thread_id", ""),
        "from": message.get("from", ""),
        "to": message.get("to", ""),
        "subject": message.get("subject", ""),
        "date": message.get("date", ""),
        "snippet": message.get("snippet", ""),
        **({"body": message.get("body", "")} if include_body else {}),
    }


def search_emails(query: str = "", limit: int = 10) -> dict:
    try:
        messages = search_messages(query=query, limit=limit)
        payload = {"query": query, "limit": limit}
        if not messages:
            return empty("email", payload)
        return success("email", [_structured_message(message) for message in messages], payload)
    except Exception as exc:
        return error("email", str(exc), {"query": query, "limit": limit})


def read_email(message_id: str) -> dict:
    if not str(message_id or "").strip():
        raise ValueError("Email message_id tələb olunur.")
    try:
        message = get_message(message_id)
        return success("email", [_structured_message(message, include_body=True)], {"message_id": message_id}, {"selected_id": f"email:{message_id}"})
    except Exception as exc:
        return error("email", str(exc), {"message_id": message_id})
