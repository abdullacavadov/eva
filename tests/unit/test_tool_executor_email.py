import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.tool_executor import ToolExecutor


def make_executor():
    ui = MagicMock()
    ui.muted = False
    webcam = MagicMock()
    return ToolExecutor(ui, webcam, MagicMock(), MagicMock())


def test_get_emails_dispatches_query_and_limit():
    executor = make_executor()
    fc = SimpleNamespace(
        id="email-search-1",
        name="get_emails",
        args={"query": "is:unread", "limit": 5},
    )
    with patch("core.tool_executor.search_emails", return_value="ID: m1") as search:
        response = asyncio.run(executor.execute(fc))
    search.assert_called_once_with("is:unread", 5)
    assert response.response["result"] == "ID: m1"


def test_trash_emails_dispatches_confirmation_id_only():
    executor = make_executor()
    fc = SimpleNamespace(
        id="email-trash-1",
        name="confirm_action",
        args={"confirmation_id": "confirm-123"},
    )
    with (
        patch("core.tool_executor.get_pending_confirmation", return_value={"action": "trash_emails", "payload": {}}),
        patch("core.tool_executor.consume_confirmation"),
        patch("core.tool_executor.trash_emails", return_value="trashed") as trash,
    ):
        response = asyncio.run(executor.execute(fc))
    trash.assert_called_once_with("confirm-123")
    assert response.response["result"] == "trashed"


def test_read_email_dispatches_message_id():
    executor = make_executor()
    fc = SimpleNamespace(
        id="email-read-1",
        name="read_email",
        args={"message_id": "abc123"},
    )
    with patch("core.tool_executor.read_email", return_value="Mövzu: Hello") as read:
        response = asyncio.run(executor.execute(fc))
    read.assert_called_once_with("abc123")
    assert response.response["result"] == "Mövzu: Hello"


def test_email_action_exception_is_not_reported_as_success():
    executor = make_executor()
    fc = SimpleNamespace(
        id="email-search-2",
        name="get_emails",
        args={"query": "", "limit": 10},
    )
    with patch("core.tool_executor.search_emails", side_effect=RuntimeError("gmail down")):
        response = asyncio.run(executor.execute(fc))
    assert response.response["result"] == "Xəta: gmail down"
    executor.ui.set_state.assert_any_call("ERROR")
