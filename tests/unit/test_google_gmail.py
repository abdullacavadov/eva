import base64
from email import message_from_bytes
from unittest.mock import MagicMock, patch

import pytest

from integrations.google.gmail import (
    create_draft,
    get_gmail_service,
    get_message,
    get_thread,
    search_messages,
    send_draft,
    trash_message,
    trash_messages_by_query,
)


def test_get_gmail_service_uses_gmail_v1():
    credentials = MagicMock()
    with patch("integrations.google.gmail.get_google_credentials", return_value=credentials), \
            patch("integrations.google.gmail.build") as build:
        get_gmail_service()
    build.assert_called_once_with("gmail", "v1", credentials=credentials)


def test_search_messages_parses_metadata_and_query():
    service = MagicMock()
    list_method = service.users.return_value.messages.return_value.list
    list_call = list_method.return_value
    list_call.execute.side_effect = [
        {
            "messages": [{"id": "m1", "threadId": "t1"}],
            "resultSizeEstimate": 1,
        }
    ]
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.return_value = {
        "id": "m1",
        "threadId": "t1",
        "snippet": "Invoice received",
        "payload": {"headers": [
            {"name": "From", "value": "billing@example.com"},
            {"name": "Subject", "value": "Invoice"},
            {"name": "Date", "value": "Wed, 19 Aug 2026 10:00:00 +0400"},
        ]},
    }

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = search_messages("subject:invoice", 1)

    assert result["messages"][0]["id"] == "m1"
    assert result["messages"][0]["from"] == "billing@example.com"
    assert result["messages"][0]["subject"] == "Invoice"
    assert result["count"] == 1
    assert result["returned_count"] == 1
    assert result["has_more"] is False
    list_call.execute.assert_called_once()
    assert list_method.call_args.kwargs["q"] == "subject:invoice"


def test_search_messages_paginates_until_limit():
    service = MagicMock()
    list_call = service.users.return_value.messages.return_value.list.return_value
    list_call.execute.side_effect = [
        {
            "messages": [{"id": "m1"}],
            "resultSizeEstimate": 2,
            "nextPageToken": "p2",
        },
        {
            "messages": [{"id": "m2"}],
            "resultSizeEstimate": 2,
        },
    ]
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.side_effect = [
        {"id": "m1", "payload": {"headers": []}},
        {"id": "m2", "payload": {"headers": []}},
    ]

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = search_messages("", 2)

    assert [item["id"] for item in result["messages"]] == ["m1", "m2"]
    assert result["count"] == 2
    assert result["returned_count"] == 2
    assert result["has_more"] is False
    assert list_call.execute.call_count == 2


def test_search_messages_caps_limit_at_100():
    service = MagicMock()
    list_method = service.users.return_value.messages.return_value.list
    list_call = list_method.return_value
    list_call.execute.return_value = {"messages": []}

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        search_messages("", 1000)

    assert list_call.execute.call_count == 1
    assert list_method.call_args.kwargs["maxResults"] == 100


def test_trash_message_uses_gmail_trash_not_delete():
    service = MagicMock()
    trash_call = service.users.return_value.messages.return_value.trash.return_value
    trash_call.execute.return_value = {"id": "m1", "threadId": "t1"}

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = trash_message("m1")

    assert result == {"message_id": "m1", "thread_id": "t1"}
    trash_call.execute.assert_called_once()
    service.users.return_value.messages.return_value.delete.assert_not_called()


def test_trash_messages_by_query_paginates_and_trashes_all_matches():
    service = MagicMock()
    list_call = service.users.return_value.messages.return_value.list.return_value
    list_call.execute.side_effect = [
        {"messages": [{"id": "m1"}], "nextPageToken": "p2"},
        {"messages": [{"id": "m2"}]},
    ]

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = trash_messages_by_query("in:spam")

    assert result == {"matched_count": 2, "trashed_count": 2}
    assert service.users.return_value.messages.return_value.trash.call_count == 2
    assert list_call.execute.call_count == 2


def test_get_message_requires_id():
    with pytest.raises(ValueError):
        get_message("")


def test_get_message_extracts_plain_text_body():
    service = MagicMock()
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.return_value = {
        "id": "m1", "threadId": "t1",
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": "Subject", "value": "Hello"}],
            "body": {"data": "SGVsbG8gQWJkdWxsYQ=="},
        },
    }
    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = get_message("m1")
    assert result["subject"] == "Hello"
    assert result["body"] == "Hello Abdulla"


def test_get_message_strips_html():
    service = MagicMock()
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.return_value = {
        "id": "m1",
        "payload": {"mimeType": "text/html", "body": {"data": "PGh0bWw+PGJvZHk+SGVsbG8gPGI+QWJkdWxsYTwvYj48L2JvZHk+PC9odG1sPg=="}},
    }
    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = get_message("m1")
    assert result["body"] == "Hello Abdulla"


def test_get_thread_requires_id():
    with pytest.raises(ValueError):
        get_thread("")


def test_get_thread_fetches_full_messages():
    service = MagicMock()
    get_method = service.users.return_value.threads.return_value.get
    get_call = get_method.return_value
    get_call.execute.return_value = {
        "id": "t1",
        "messages": [
            {"id": "m1", "threadId": "t1", "payload": {"headers": [{"name": "From", "value": "a@example.com"}, {
                "name": "Message-ID", "value": "<m1@example.com>"}], "body": {"data": "SGVsbG8="}}},
            {"id": "m2", "threadId": "t1", "payload": {"headers": [
                {"name": "From", "value": "b@example.com"}], "body": {"data": "UmVwbHk="}}},
        ],
    }
    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = get_thread("t1")
    assert [item["id"] for item in result] == ["m1", "m2"]
    assert result[0]["thread_id"] == "t1"
    assert result[0]["message_id_header"] == "<m1@example.com>"
    assert result[0]["body"] == "Hello"
    get_method.assert_called_once_with(userId="me", id="t1", format="full")


def test_create_draft_requires_recipient_subject_and_body():
    with pytest.raises(ValueError, match="recipient"):
        create_draft("", "Subject", "Body")
    with pytest.raises(ValueError, match="subject"):
        create_draft("a@example.com", "", "Body")
    with pytest.raises(ValueError, match="body"):
        create_draft("a@example.com", "Subject", "")


def test_create_draft_builds_mime_and_thread_headers():
    service = MagicMock()
    create_method = service.users.return_value.drafts.return_value.create
    create_call = create_method.return_value
    create_call.execute.return_value = {
        "id": "d1",
        "message": {"id": "m1", "threadId": "t1"},
    }

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = create_draft(
            "a@example.com",
            "Re: Hello",
            "Reply body",
            "cc@example.com",
            "bcc@example.com",
            "t1",
            "<m1@example.com>",
            "<root@example.com> <m1@example.com>",
        )

    assert result == {
        "draft_id": "d1",
        "gmail_message_id": "m1",
        "thread_id": "t1",
    }

    request = create_method.call_args.kwargs["body"]

    assert request["message"]["threadId"] == "t1"

    raw = base64.urlsafe_b64decode(request["message"]["raw"])
    parsed = message_from_bytes(raw)

    assert parsed["To"] == "a@example.com"
    assert parsed["Cc"] == "cc@example.com"
    assert parsed["Bcc"] == "bcc@example.com"
    assert parsed["Subject"] == "Re: Hello"
    assert parsed["In-Reply-To"] == "<m1@example.com>"
    assert parsed["References"] == "<root@example.com> <m1@example.com>"
    assert parsed.get_payload().strip() == "Reply body"


def test_create_draft_new_email_does_not_set_thread_id():
    service = MagicMock()
    create_method = service.users.return_value.drafts.return_value.create
    create_call = create_method.return_value
    create_call.execute.return_value = {
        "id": "d1",
        "message": {"id": "m1", "threadId": "t1"},
    }

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        create_draft("a@example.com", "Hello", "Body")

    request = create_method.call_args.kwargs["body"]
    assert "threadId" not in request["message"]


def test_send_draft_requires_id():
    with pytest.raises(ValueError):
        send_draft("")


def test_send_draft_sends_existing_draft():
    service = MagicMock()
    send_method = service.users.return_value.drafts.return_value.send
    send_call = send_method.return_value
    send_call.execute.return_value = {"id": "m1", "threadId": "t1"}

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = send_draft("d1")

    assert result == {"message_id": "m1", "thread_id": "t1"}
    send_method.assert_called_once_with(userId="me", body={"id": "d1"})
