from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from core.whatsapp import conversation_result, empty_conversations, empty_messages, message_result
from integrations.whatsapp.web import (
    WhatsAppVisibleConversation,
    WhatsAppVisibleMessage,
    WhatsAppWebBridge,
)

_SEEN_LIMIT = 2000


def _fingerprint(message: WhatsAppVisibleMessage) -> str:
    raw = "\x1f".join(
        (
            message.conversation_id,
            message.timestamp,
            message.sender,
            message.content,
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _message_key(message: WhatsAppVisibleMessage) -> str:
    return message.message_id or _fingerprint(message)


def _load_seen(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    values = payload.get("message_ids", []) if isinstance(payload, dict) else []
    return [str(value) for value in values][- _SEEN_LIMIT :]


def _save_seen(path: Path, values: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = list(dict.fromkeys(str(value) for value in values))[-_SEEN_LIMIT:]
    path.write_text(json.dumps({"message_ids": unique}, ensure_ascii=False, indent=2), encoding="utf-8")


def read_visible_whatsapp_messages(
    bridge: WhatsAppWebBridge,
    seen_path: str | Path,
) -> dict[str, Any]:
    path = Path(seen_path)
    seen = _load_seen(path)
    seen_set = set(seen)
    new_messages: list[WhatsAppVisibleMessage] = []

    for message in bridge.get_visible_messages():
        key = _message_key(message)
        if key in seen_set:
            continue
        seen_set.add(key)
        seen.append(key)
        new_messages.append(message)

    _save_seen(path, seen)

    if not new_messages:
        return empty_messages(meta={"deduplicated": True})

    items = [
        message_result(
            message_id=message.message_id or _fingerprint(message),
            conversation_id=message.conversation_id,
            sender=message.sender,
            sender_phone=message.sender_phone,
            content=message.content,
            timestamp=message.timestamp,
            direction=message.direction,
        )["data"][0]
        for message in new_messages
    ]

    return {
        "type": "whatsapp_message",
        "status": "success",
        "query": {"scope": "visible"},
        "data": items,
        "count": len(items),
        "selected": None,
        "meta": {"deduplicated": True},
    }


def read_visible_whatsapp_conversations(
    bridge: WhatsAppWebBridge,
) -> dict[str, Any]:
    conversations = bridge.get_visible_conversations()
    if not conversations:
        return empty_conversations(meta={"scope": "visible"})

    items = [
        conversation_result(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            contact_name=conversation.contact_name,
            contact_phone=conversation.contact_phone,
            last_message=conversation.last_message,
            last_message_timestamp=conversation.last_message_timestamp,
            unread_count=conversation.unread_count,
        )["data"][0]
        for conversation in conversations
    ]

    return {
        "type": "whatsapp_conversation",
        "status": "success",
        "query": {"scope": "visible"},
        "data": items,
        "count": len(items),
        "selected": None,
        "meta": {"scope": "visible"},
    }
