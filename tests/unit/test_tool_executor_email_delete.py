import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.tool_executor import ToolExecutor


def make_executor():
    ui = MagicMock()
    ui.muted = False
    webcam = MagicMock()
    return ToolExecutor(ui, webcam, MagicMock(), MagicMock())


def test_prepare_email_deletion_dispatches_scope_and_draft_id():
    executor = make_executor()
    fc = SimpleNamespace(
        id="email-delete-prepare-1",
        name="prepare_email_deletion",
        args={"scope": "draft", "draft_id": "d1"},
    )
    structured = {
        "type": "email",
        "status": "success",
        "query": {"scope": "draft", "draft_id": "d1"},
        "data": [{"id": "email:delete:token", "target_count": 1}],
        "count": 1,
        "selected": None,
        "meta": {"requires_confirmation": True},
    }
    with patch("core.tool_executor.prepare_email_deletion", return_value=structured) as prepare:
        response = asyncio.run(executor.execute(fc))

    prepare.assert_called_once_with("draft", "d1")
    assert response.response["result"] == structured


def test_delete_email_dispatches_confirmation_id():
    executor = make_executor()
    fc = SimpleNamespace(
        id="email-delete-1",
        name="confirm_action",
        args={"confirmation_id": "token-1"},
    )
    structured = {
        "type": "email",
        "status": "success",
        "query": {"scope": "drafts"},
        "data": [{"deleted_count": 3}],
        "count": 1,
        "selected": None,
        "meta": {"requires_confirmation": False},
    }
    with (
        patch("core.tool_executor.get_pending_confirmation", return_value={"action": "delete_email", "payload": {}}),
        patch("core.tool_executor.consume_confirmation"),
        patch("core.tool_executor.delete_email", return_value=structured) as delete,
    ):
        response = asyncio.run(executor.execute(fc))

    delete.assert_called_once_with("token-1")
    assert response.response["result"] == structured
