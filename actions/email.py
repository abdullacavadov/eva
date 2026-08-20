from __future__ import annotations

from integrations.google.gmail import (
    create_draft,
    get_message,
    get_thread,
    search_messages,
    send_draft,
)
from core.results import empty, error, success


def _structured_message(message: dict[str, str], include_body: bool = False) -> dict:
    return {
        "id": f"email:{message.get('id', '')}",
        "gmail_message_id": message.get("id", ""),
        "thread_id": message.get("thread_id", ""),
        "from": message.get("from", ""),
        "to": message.get("to", ""),
        "cc": message.get("cc", ""),
        "bcc": message.get("bcc", ""),
        "subject": message.get("subject", ""),
        "date": message.get("date", ""),
        "snippet": message.get("snippet", ""),
        "message_id_header": message.get("message_id_header", ""),
        "references": message.get("references", ""),
        "in_reply_to": message.get("in_reply_to", ""),
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


def read_email_thread(thread_id: str) -> dict:
    if not str(thread_id or "").strip():
        raise ValueError("Email thread_id tələb olunur.")

    try:
        messages = get_thread(thread_id)

        if not messages:
            return empty(
                "email",
                {"thread_id": thread_id},
            )

        return success(
            "email",
            [
                _structured_message(message, include_body=True)
                for message in messages
            ],
            {"thread_id": thread_id},
            {
                "selected_id": f"email:{messages[-1].get('id', '')}",
                "thread_id": thread_id,
            },
        )
    except Exception as exc:
        return error(
            "email",
            str(exc),
            {"thread_id": thread_id},
        )


def prepare_email_reply(
    message_id: str,
    body: str,
) -> dict:
    if not str(message_id or "").strip():
        raise ValueError("Email message_id tələb olunur.")

    if not str(body or "").strip():
        raise ValueError("Reply body boş ola bilməz.")

    try:
        original = get_message(message_id)

        recipient = original.get("from", "").strip()
        if not recipient:
            raise ValueError("Reply üçün göndərən email ünvanı tapılmadı.")

        subject = original.get("subject", "").strip()
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        draft = create_draft(
            to=recipient,
            subject=subject,
            body=body,
            thread_id=original.get("thread_id", ""),
            in_reply_to=original.get("message_id_header", ""),
            references=(
                f"{original.get('references', '')} "
                f"{original.get('message_id_header', '')}"
            ).strip(),
        )

        item = {
            "id": f"email:draft:{draft['draft_id']}",
            "draft_id": draft["draft_id"],
            "gmail_message_id": draft["gmail_message_id"],
            "thread_id": draft["thread_id"],
            "to": recipient,
            "subject": subject,
            "body": body,
            "action": "reply",
            "status": "draft",
            "source_message_id": message_id,
        }

        return success(
            "email",
            [item],
            {
                "action": "reply",
                "message_id": message_id,
            },
            {
                "selected_id": item["id"],
                "requires_confirmation": True,
                "confirmation_action": "send_email",
            },
        )

    except Exception as exc:
        return error(
            "email",
            str(exc),
            {
                "action": "reply",
                "message_id": message_id,
            },
        )


def prepare_new_email(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
) -> dict:
    try:
        draft = create_draft(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
        )

        item = {
            "id": f"email:draft:{draft['draft_id']}",
            "draft_id": draft["draft_id"],
            "gmail_message_id": draft["gmail_message_id"],
            "thread_id": draft["thread_id"],
            "to": to,
            "cc": cc,
            "bcc": bcc,
            "subject": subject,
            "body": body,
            "action": "new",
            "status": "draft",
        }

        return success(
            "email",
            [item],
            {
                "action": "new",
                "to": to,
                "subject": subject,
            },
            {
                "selected_id": item["id"],
                "requires_confirmation": True,
                "confirmation_action": "send_email",
            },
        )

    except Exception as exc:
        return error(
            "email",
            str(exc),
            {
                "action": "new",
                "to": to,
                "subject": subject,
            },
        )


def send_email(draft_id: str) -> dict:
    if not str(draft_id or "").strip():
        raise ValueError("Email draft_id tələb olunur.")

    try:
        sent = send_draft(draft_id)

        item = {
            "id": f"email:sent:{sent['message_id']}",
            "gmail_message_id": sent["message_id"],
            "thread_id": sent["thread_id"],
            "draft_id": draft_id,
            "action": "send",
            "status": "sent",
        }

        return success(
            "email",
            [item],
            {
                "draft_id": draft_id,
            },
            {
                "selected_id": item["id"],
            },
        )

    except Exception as exc:
        return error(
            "email",
            str(exc),
            {
                "draft_id": draft_id,
            },
        )
