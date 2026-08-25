from unittest.mock import Mock, patch

import pytest

from core.follow_up_execution import FollowUpExecutionError, execute_follow_up_dispatch
from core.tool_executor import FollowUpDispatch


def test_complete_dispatch_uses_real_reminder_action_by_default():
    dispatch = FollowUpDispatch(
        "complete_reminder",
        {"task_id": "t2", "list_name": "list1"},
        {"id": "task:t2"},
    )
    result = {
        "type": "task",
        "status": "success",
        "data": [{"id": "task:t2", "status": "completed"}],
        "count": 1,
    }

    with patch("core.follow_up_execution.complete_reminder", return_value=result) as complete:
        actual = execute_follow_up_dispatch(dispatch)

    complete.assert_called_once_with(task_id="t2", list_name="list1")
    assert actual == result


def test_delete_dispatch_without_confirmation_fails_closed():
    dispatch = FollowUpDispatch(
        "delete_reminder",
        {"task_id": "t2", "list_name": "list1"},
        {"id": "task:t2"},
        confirmation_required=False,
    )

    with pytest.raises(FollowUpExecutionError, match="confirmation"):
        execute_follow_up_dispatch(dispatch, delete_task=Mock())


def test_complete_dispatch_updates_result_store_with_structured_result():
    result_store = Mock()
    result = {
        "type": "task",
        "status": "success",
        "data": [{"id": "task:t2", "status": "completed"}],
        "count": 1,
    }
    dispatch = FollowUpDispatch(
        "complete_reminder",
        {"task_id": "t2", "list_name": "list1"},
        {"id": "task:t2"},
    )

    with patch("core.follow_up_execution.complete_reminder", return_value=result):
        actual = execute_follow_up_dispatch(dispatch, result_store=result_store)

    assert actual == result
    result_store.save.assert_called_once_with(result)
