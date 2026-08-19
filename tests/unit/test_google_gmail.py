from unittest.mock import MagicMock, patch

import pytest

from integrations.google.gmail import get_gmail_service, get_message, search_messages


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
        {"messages": [{"id": "m1", "threadId": "t1"}]}
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

    assert result[0]["id"] == "m1"
    assert result[0]["from"] == "billing@example.com"
    assert result[0]["subject"] == "Invoice"
    list_call.execute.assert_called_once()
    assert list_method.call_args.kwargs["q"] == "subject:invoice"


def test_search_messages_paginates_until_limit():
    service = MagicMock()
    list_call = service.users.return_value.messages.return_value.list.return_value
    list_call.execute.side_effect = [
        {"messages": [{"id": "m1"}], "nextPageToken": "p2"},
        {"messages": [{"id": "m2"}]},
    ]
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.side_effect = [
        {"id": "m1", "payload": {"headers": []}},
        {"id": "m2", "payload": {"headers": []}},
    ]

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = search_messages("", 2)

    assert [item["id"] for item in result] == ["m1", "m2"]
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


def test_get_message_requires_id():
    with pytest.raises(ValueError):
        get_message("")


def test_get_message_extracts_plain_text_body():
    service = MagicMock()
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.return_value = {
        "id": "m1",
        "threadId": "t1",
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
        "payload": {
            "mimeType": "text/html",
            "body": {"data": "PGh0bWw+PGJvZHk+SGVsbG8gPGI+QWJkdWxsYTwvYj48L2JvZHk+PC9odG1sPg=="},
        },
    }

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = get_message("m1")

    assert result["body"] == "Hello Abdulla"
