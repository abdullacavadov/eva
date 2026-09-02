from unittest.mock import MagicMock, patch

from integrations.google.gmail import search_messages


def test_search_messages_uses_exact_count_beyond_limit():
    service = MagicMock()
    list_call = service.users.return_value.messages.return_value.list.return_value
    list_call.execute.side_effect = [
        {
            "messages": [{"id": "m1"}, {"id": "m2"}],
            "nextPageToken": "p2",
            "resultSizeEstimate": 201,
        },
        {
            "messages": [{"id": "m3"}],
        },
    ]
    get_call = service.users.return_value.messages.return_value.get.return_value
    get_call.execute.return_value = {
        "id": "m1",
        "payload": {"headers": []},
    }

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = search_messages("is:unread", 1)

    assert result["count"] == 3
    assert result["returned_count"] == 1
    assert result["has_more"] is True
    assert [item["id"] for item in result["messages"]] == ["m1"]
    assert list_call.execute.call_count == 2
    assert get_call.execute.call_count == 1
