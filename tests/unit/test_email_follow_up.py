import pytest

from core.email_follow_up import build_email_follow_up, execute_email_follow_up
from core.result_resolver import FollowUpAction, ResultResolutionError


def _item():
    return {
        "id": "email:m1",
        "gmail_message_id": "m1",
        "thread_id": "t1",
        "subject": "Test email",
        "from": "sender@example.com",
    }


def test_email_show_builds_read_dispatch():
    dispatch = build_email_follow_up(FollowUpAction("ikincini", "show", _item(), "göstər"))
    assert dispatch["tool_name"] == "read_email"
    assert dispatch["args"]["message_id"] == "m1"


def test_email_reply_requires_confirmation_and_body():
    dispatch = build_email_follow_up(FollowUpAction("buna", "reply", _item(), "cavab yaz"), reply_body="Salam")
    assert dispatch["tool_name"] == "prepare_email_reply"
    assert dispatch["args"] == {"message_id": "m1", "body": "Salam"}
    assert dispatch["confirmation_required"] is True


def test_email_delete_routes_to_trash_confirmation():
    dispatch = build_email_follow_up(FollowUpAction("onu", "delete", _item(), "sil"))
    assert dispatch["tool_name"] == "prepare_trash_emails"
    assert dispatch["args"]["message_id"] == "m1"
    assert dispatch["confirmation_required"] is True
    assert execute_email_follow_up(dispatch)["status"] == "confirmation_required"


def test_email_reply_rejects_empty_body():
    with pytest.raises(ResultResolutionError):
        build_email_follow_up(FollowUpAction("buna", "reply", _item(), "cavab yaz"))
