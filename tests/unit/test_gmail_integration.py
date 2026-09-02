from unittest.mock import Mock, patch

from integrations.google.gmail import get_unread_inbox_count, search_messages


def _request(execute_value):
    request = Mock()
    request.execute.return_value = execute_value
    return request


def test_unread_inbox_count_uses_inbox_label_messages_unread():
    service = Mock()
    service.users.return_value.labels.return_value.get.return_value = _request(
        {"messagesTotal": 500, "messagesUnread": 17}
    )
    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        assert get_unread_inbox_count() == 17
    service.users.return_value.labels.return_value.get.assert_called_once_with(
        userId="me", id="INBOX"
    )


def test_search_messages_counts_all_pages_but_fetches_only_requested_limit():
    service = Mock()
    first_list = _request({
        "messages": [{"id": "m1"}],
        "nextPageToken": "next",
    })
    second_list = _request({"messages": [{"id": "m2"}]})
    message_1 = _request({
        "id": "m1", "threadId": "t1", "snippet": "one",
        "payload": {"headers": [{"name": "Subject", "value": "One"}]},
    })
    message_2 = _request({
        "id": "m2", "threadId": "t2", "snippet": "two",
        "payload": {"headers": [{"name": "Subject", "value": "Two"}]},
    })
    service.users.return_value.messages.return_value.list.side_effect = [first_list, second_list]
    service.users.return_value.messages.return_value.get.side_effect = [message_1, message_2]

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = search_messages("is:unread", limit=2)

    assert result["count"] == 2
    assert result["returned_count"] == 2
    assert result["has_more"] is False
    assert [item["id"] for item in result["messages"]] == ["m1", "m2"]
    assert service.users.return_value.messages.return_value.get.call_count == 2

    list_calls = service.users.return_value.messages.return_value.list.call_args_list
    assert list_calls[0].kwargs["q"] == "is:unread"
    assert "pageToken" not in list_calls[0].kwargs
    assert list_calls[1].kwargs["pageToken"] == "next"
