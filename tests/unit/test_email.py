from unittest.mock import patch

from actions.email import read_email, search_emails


def test_search_emails_returns_structured_results():
    messages = [{
        "id": "m1", "from": "a@example.com", "to": "b@example.com",
        "subject": "Invoice", "date": "Wed", "snippet": "Invoice attached",
    }]
    with patch("actions.email.search_messages", return_value=messages):
        result = search_emails("subject:invoice", 5)
    assert result["type"] == "email"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "email:m1"
    assert result["data"][0]["gmail_message_id"] == "m1"
    assert result["data"][0]["subject"] == "Invoice"


def test_search_emails_empty_result():
    with patch("actions.email.search_messages", return_value=[]):
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
