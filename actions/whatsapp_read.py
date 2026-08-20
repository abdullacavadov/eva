from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from core.results import empty, success
from core.whatsapp import conversation_result, message_result

SEEN_MESSAGES_PATH = Path("memory/whatsapp_seen_messages.json")
MAX_SEEN_MESSAGES = 2000


def _message_key(message: object) -> str:
    message_id = str(getattr(message, "message_id", "") or "").strip()
    if message_id:
        return message_id

    raw = "|".join(
        [
            str(getattr(message, "conversation_id", "") or ""),
            str(getattr(message, "timestamp", "") or ""),
            str(getattr(message, "sender", "") or ""),
            str(getattr(message, "content", "") or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_seen(path: Path = SEEN_MESSAGES_PATH) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    values = payload.get("message_ids", []) if isinstance(payload, dict) else []
    return [str(value) for value in values][-MAX_SEEN_MESSAGES:]


def _save_seen(values: Iterable[str], path: Path = SEEN_MESSAGES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = list(dict.fromkeys(str(value) for value in values))[-MAX_SEEN_MESSAGES:]
    path.write_text(
        json.dumps({"message_ids": unique}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_visible_whatsapp_messages(bridge: object, *, seen_path: Path = SEEN_MESSAGES_PATH) -> dict:
    seen = _load_seen(seen_path)
    seen_set = set(seen)
    fresh = []

    for message in bridge.get_visible_messages():
        key = _message_key(message)
        if key in seen_set:
            continue
        seen_set.add(key)
        seen.append(key)
        fresh.append(message)

    _save_seen(seen, seen_path)

    if not fresh:
        return empty(
            "whatsapp_message",
            query={},
            meta={"deduplicated": True},
        )

    items = []
    for message in fresh:
        result = message_result(
            message_id=message.message_id,
            conversation_id=message.conversation_id,
            sender=message.sender,
            sender_phone=message.sender_phone,
            content=message.content,
            timestamp=message.timestamp,
            direction=message.direction,
        )
        items.extend(result.get("data", []))

    return success(
        "whatsapp_message",
        items,
        query={},
        meta={"deduplicated": True},
    )


def read_visible_whatsapp_conversations(bridge: object) -> dict:
    conversations = bridge.get_visible_conversations()
    items = []
    for conversation in conversations:
        result = conversation_result(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            contact_name=conversation.contact_name,
            contact_phone=conversation.contact_phone,
            last_message=conversation.last_message,
            last_message_timestamp=conversation.last_message_timestamp,
        )
        items.extend(result.get("data", []))

    if not items:
        return empty("whatsapp_conversation", query={}, meta={})

    return success(
        "whatsapp_conversation",
        items,
        query={},
        meta={},
    )
