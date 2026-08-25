"""Gmail follow-up routing for conversational actions."""

from __future__ import annotations

from actions.email import prepare_email_reply, prepare_trash_emails, read_email
from core.result_resolver import FollowUpAction, ResultResolutionError


def build_email_follow_up(action: FollowUpAction, *, reply_body: str = "") -> dict:
    item = action.item
    item_id = str(item.get("id", ""))
    if not item_id.startswith("email:"):
        raise ResultResolutionError("Email follow-up üçün email nəticəsi tələb olunur")
    message_id = str(item.get("gmail_message_id", ""))
    if not message_id:
        message_id = item_id.removeprefix("email:")
    if not message_id or message_id.startswith("draft:") or message_id.startswith("delete:"):
        raise ResultResolutionError("Email message identifikatoru tapılmadı")

    if action.action == "show":
        return {"tool_name": "read_email", "args": {"message_id": message_id}, "item": item}

    if action.action == "reply":
        body = str(reply_body or "").strip()
        if not body:
            raise ResultResolutionError("Email cavabı üçün reply mətni tələb olunur")
        return {
            "tool_name": "prepare_email_reply",
            "args": {"message_id": message_id, "body": body},
            "item": item,
            "confirmation_required": True,
        }

    if action.action == "delete":
        return {
            "tool_name": "prepare_trash_emails",
            "args": {"message_id": message_id},
            "item": item,
            "confirmation_required": True,
        }

    raise ResultResolutionError("Email üçün dəstəklənməyən follow-up əməli")


def execute_email_follow_up(dispatch: dict) -> dict:
    if dispatch.get("confirmation_required"):
        return {"status": "confirmation_required", **dispatch}
    tool = dispatch.get("tool_name")
    args = dict(dispatch.get("args", {}))
    if tool == "read_email":
        return read_email(**args)
    if tool == "prepare_email_reply":
        raise ResultResolutionError("Email reply üçün confirmation tələb olunur")
    if tool == "prepare_trash_emails":
        raise ResultResolutionError("Email silmə üçün confirmation tələb olunur")
    raise ResultResolutionError("Email follow-up dispatch tanınmadı")
