from unittest.mock import patch

from actions.email import (
    prepare_email_reply,
    prepare_new_email,
    read_email,
    read_email_thread,
    search_emails,
    send_email,
)


def test_search_emails_returns_structured_results():
    messages = [{
        "id": "m1", "from": "a@example.com", "to": "b@example.com",
        "subject": "Invoice", "date": "Wed", "snippet": "Invoice attached",
    }]
    with patch(
        "actions.email.search_messages",
        return_value={
            "messages": messages,
            "count": 1,
            "returned_count": 1,
            "has_more": False,
        },
    ):
        result = search_emails("subject:invoice", 5)
    assert result["type"] == "email"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "email:m1"
    assert result["data"][0]["gmail_message_id"] == "m1"
    assert result["data"][0]["subject"] == "Invoice"


def test_search_emails_empty_result():
    with patch(
        "actions.email.search_messages",
        return_value={
            "messages": [],
            "count": 0,
            "returned_count": 0,
            "has_more": False,
        },
    ):
        result = search_emails("from:nobody", 5)
    assert result["type"] == "email"
    assert result["status"] == "empty"
    assert result["count"] == 0
    assert result["data"] == []


def test_search_emails_passes_query_and_limit():
    with patch("actions.email.search_messages", return_value=[]) as search:
        search_emails("is:unread", 7)
    search.assert_called_once_with(query="is:unread", limit=7)


def test_read_email_returns_body_structured():
    message = {
        "id": "m1", "from": "a@example.com", "to": "b@example.com",
        "subject": "Hello", "date": "Wed", "body": "Hello Abdulla",
    }
    with patch("actions.email.get_message", return_value=message):
        result = read_email("m1")
    assert result["status"] == "success"
    assert result["selected"] is None
    assert result["data"][0]["body"] == "Hello Abdulla"


def test_read_email_propagates_missing_id_error():
    with patch("actions.email.get_message", side_effect=ValueError("Email message_id tələb olunur.")):
        try:
            read_email("")
        except ValueError as exc:
            assert "message_id" in str(exc)
        else:
            raise AssertionError("ValueError gözlənilirdi")


def test_read_email_thread_returns_structured_messages():
    messages = [
        {"id": "m1", "thread_id": "t1", "from": "a@example.com", "body": "Hello"},
        {"id": "m2", "thread_id": "t1", "from": "b@example.com", "body": "Reply"},
    ]
    with patch("actions.email.get_thread", return_value=messages):
        result = read_email_thread("t1")

    assert result["type"] == "email"
    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["meta"]["thread_id"] == "t1"
    assert result["data"][1]["body"] == "Reply"


def test_prepare_email_reply_creates_confirmable_draft():
    original = {
        "id": "m1",
        "thread_id": "t1",
        "from": "sender@example.com",
        "subject": "Hello",
        "message_id_header": "<m1@example.com>",
        "references": "<root@example.com>",
    }
    draft = {
        "draft_id": "d1",
        "gmail_message_id": "draft-message",
        "thread_id": "t1",
    }

    with patch("actions.email.get_message", return_value=original), \
         patch("actions.email.create_draft", return_value=draft) as create:
        result = prepare_email_reply("m1", "Reply body")

    create.assert_called_once_with(
        to="sender@example.com",
        subject="Re: Hello",
        body="Reply body",
        thread_id="t1",
        in_reply_to="<m1@example.com>",
        references="<root@example.com> <m1@example.com>",
    )
    item = result["data"][0]
    assert item["draft_id"] == "d1"
    assert item["action"] == "reply"
    assert item["status"] == "draft"
    assert result["meta"]["requires_confirmation"] is True
    assert result["meta"]["confirmation_action"] == "send_email"


def test_prepare_email_reply_does_not_duplicate_re_prefix():
    original = {
        "id": "m1",
        "thread_id": "t1",
        "from": "sender@example.com",
        "subject": "Re: Hello",
        "message_id_header": "<m1@example.com>",
        "references": "",
    }
    draft = {"draft_id": "d1", "gmail_message_id": "m2", "thread_id": "t1"}

    with patch("actions.email.get_message", return_value=original), \
         patch("actions.email.create_draft", return_value=draft) as create:
        prepare_email_reply("m1", "Reply")

    assert create.call_args.kwargs["subject"] == "Re: Hello"


def test_prepare_new_email_returns_confirmable_draft():
    draft = {
        "draft_id": "d1",
        "gmail_message_id": "m1",
        "thread_id": "t1",
    }
    with patch("actions.email.create_draft", return_value=draft) as create:
        result = prepare_new_email(
            "a@example.com",
            "Hello",
            "Body",
            "cc@example.com",
            "bcc@example.com",
        )

    create.assert_called_once_with(
        to="a@example.com",
        subject="Hello",
        body="Body",
        cc="cc@example.com",
        bcc="bcc@example.com",
    )
    item = result["data"][0]
    assert item["draft_id"] == "d1"
    assert item["action"] == "new"
    assert item["status"] == "draft"
    assert result["meta"]["requires_confirmation"] is True


def test_send_email_sends_only_existing_draft():
    sent = {"message_id": "m1", "thread_id": "t1"}
    with patch("actions.email.send_draft", return_value=sent) as send:
        result = send_email("d1")

    send.assert_called_once_with("d1")
    item = result["data"][0]
    assert item["draft_id"] == "d1"
    assert item["gmail_message_id"] == "m1"
    assert item["status"] == "sent"


def test_send_email_missing_draft_id_is_rejected():
    with patch("actions.email.send_draft") as send:
        try:
            send_email("")
        except ValueError as exc:
            assert "draft_id" in str(exc)
        else:
            raise AssertionError("ValueError gözlənilirdi")
        send.assert_not_called()


def test_search_emails_preserves_total_count_when_paginated():
    messages = [
        {
            "id": f"m{i}",
            "from": "a@example.com",
            "to": "b@example.com",
            "subject": "Invoice",
            "date": "Wed",
            "snippet": "Invoice attached",
        }
        for i in range(10)
    ]

    with patch(
        "actions.email.search_messages",
        return_value={
            "messages": messages,
            "count": 28,
            "returned_count": 10,
            "has_more": True,
        },
    ):
        result = search_emails("subject:invoice", 10)

    assert result["status"] == "success"
    assert result["count"] == 28
    assert result["meta"]["returned_count"] == 10
    assert result["meta"]["has_more"] is True