from __future__ import annotations

from typing import Any

from core.results import empty, error, success


def _message_item(
    *,
    message_id: str,
    conversation_id: str,
    sender: str = "",
    sender_phone: str = "",
    content: str = "",
    timestamp: str = "",
    direction: str = "incoming",
) -> dict[str, Any]:
    message_id = str(message_id or "").strip()
    conversation_id = str(conversation_id or "").strip()

    if not message_id:
        raise ValueError("WhatsApp message_id tələb olunur.")
    if not conversation_id:
        raise ValueError("WhatsApp conversation_id tələb olunur.")

    direction = str(direction or "").strip().lower()
    if direction not in {"incoming", "outgoing"}:
        raise ValueError("WhatsApp message direction düzgün deyil.")

    return {
        "id": f"whatsapp:message:{message_id}",
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender": str(sender or "").strip(),
        "sender_phone": str(sender_phone or "").strip(),
        "content": str(content or ""),
        "timestamp": str(timestamp or "").strip(),
        "direction": direction,
    }


def _conversation_item(
    *,
    conversation_id: str,
    title: str = "",
    contact_name: str = "",
    contact_phone: str = "",
    last_message: str = "",
    last_message_timestamp: str = "",
    unread_count: int = 0,
) -> dict[str, Any]:
    conversation_id = str(conversation_id or "").strip()

    if not conversation_id:
        raise ValueError("WhatsApp conversation_id tələb olunur.")

    return {
        "id": f"whatsapp:conversation:{conversation_id}",
        "conversation_id": conversation_id,
        "title": str(title or "").strip(),
        "contact_name": str(contact_name or "").strip(),
        "contact_phone": str(contact_phone or "").strip(),
        "last_message": str(last_message or ""),
        "last_message_timestamp": str(last_message_timestamp or "").strip(),
        "unread_count": int(unread_count or 0),
    }


def _draft_item(
    *,
    draft_id: str,
    conversation_id: str,
    recipient_name: str = "",
    recipient_phone: str = "",
    content: str = "",
    action: str = "reply",
    source_message_id: str = "",
) -> dict[str, Any]:
    draft_id = str(draft_id or "").strip()
    conversation_id = str(conversation_id or "").strip()
    content = str(content or "")

    if not draft_id:
        raise ValueError("WhatsApp draft_id tələb olunur.")
    if not conversation_id:
        raise ValueError("WhatsApp conversation_id tələb olunur.")
    if not content.strip():
        raise ValueError("WhatsApp draft mesajı boş ola bilməz.")

    action = str(action or "").strip().lower()
    if action not in {"reply", "new"}:
        raise ValueError("WhatsApp draft action düzgün deyil.")

    return {
        "id": f"whatsapp:draft:{draft_id}",
        "draft_id": draft_id,
        "conversation_id": conversation_id,
        "recipient_name": str(recipient_name or "").strip(),
        "recipient_phone": str(recipient_phone or "").strip(),
        "content": content,
        "action": action,
        "status": "draft",
        "source_message_id": str(source_message_id or "").strip(),
    }


def message_result(
    *,
    message_id: str,
    conversation_id: str,
    sender: str = "",
    sender_phone: str = "",
    content: str = "",
    timestamp: str = "",
    direction: str = "incoming",
    query: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        item = _message_item(
            message_id=message_id,
            conversation_id=conversation_id,
            sender=sender,
            sender_phone=sender_phone,
            content=content,
            timestamp=timestamp,
            direction=direction,
        )
        return success(
            "whatsapp_message",
            [item],
            query=query,
            meta=meta,
        )
    except Exception as exc:
        return error(
            "whatsapp_message",
            str(exc),
            query,
        )


def conversation_result(
    *,
    conversation_id: str,
    title: str = "",
    contact_name: str = "",
    contact_phone: str = "",
    last_message: str = "",
    last_message_timestamp: str = "",
    unread_count: int = 0,
    query: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        item = _conversation_item(
            conversation_id=conversation_id,
            title=title,
            contact_name=contact_name,
            contact_phone=contact_phone,
            last_message=last_message,
            last_message_timestamp=last_message_timestamp,
            unread_count=unread_count,
        )
        return success(
            "whatsapp_conversation",
            [item],
            query=query,
            meta=meta,
        )
    except Exception as exc:
        return error(
            "whatsapp_conversation",
            str(exc),
            query,
        )


def draft_result(
    *,
    draft_id: str,
    conversation_id: str,
    recipient_name: str = "",
    recipient_phone: str = "",
    content: str = "",
    action: str = "reply",
    source_message_id: str = "",
    query: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        item = _draft_item(
            draft_id=draft_id,
            conversation_id=conversation_id,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            content=content,
            action=action,
            source_message_id=source_message_id,
        )

        result_meta = {
            "requires_confirmation": True,
            "confirmation_action": "send_whatsapp_message",
            **(meta or {}),
        }

        return success(
            "whatsapp_draft",
            [item],
            query=query,
            meta=result_meta,
        )
    except Exception as exc:
        return error(
            "whatsapp_draft",
            str(exc),
            query,
        )


def empty_messages(
    query: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return empty("whatsapp_message", query=query, meta=meta)


def empty_conversations(
    query: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return empty("whatsapp_conversation", query=query, meta=meta)
