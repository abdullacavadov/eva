from unittest.mock import Mock

from core.follow_up_execution import execute_follow_up_dispatch
from core.tool_executor import FollowUpDispatch


def test_complete_dispatch_executes_target_and_saves_structured_result():
    result_store = Mock()
    complete = Mock(return_value={
        "type": "task",
        "status": "success",
        "data": [{"id": "task:t2", "title": "İkinci", "status": "completed"}],
        "count": 1,
    })
    dispatch = FollowUpDispatch(
        "complete_reminder",
        {"task_id": "t2", "list_name": "list1"},
        {"id": "task:t2", "google_task_id": "t2"},
    )

    result = execute_follow_up_dispatch(
        dispatch,
        complete_task=complete,
        delete_task=Mock(),
        result_store=result_store,
    )

    complete.assert_called_once_with(task_id="t2", list_name="list1")
    result_store.save.assert_called_once_with(result)
    assert result["data"][0]["status"] == "completed"


def test_delete_dispatch_never_bypasses_confirmation():
    delete = Mock()
    dispatch = FollowUpDispatch(
        "delete_reminder",
        {"task_id": "t2", "list_name": "list1"},
        {"id": "task:t2"},
        confirmation_required=True,
    )

    result = execute_follow_up_dispatch(
        dispatch,
        complete_task=Mock(),
        delete_task=delete,
    )

    delete.assert_not_called()
    assert result["status"] == "confirmation_required"
    assert result["args"]["task_id"] == "t2"


def test_show_dispatch_returns_resolved_item_without_action():
    item = {"id": "task:t2", "title": "İkinci"}
    dispatch = FollowUpDispatch(None, {}, item)

    result = execute_follow_up_dispatch(
        dispatch,
        complete_task=Mock(),
        delete_task=Mock(),
    )

    assert result == {"status": "resolved", "item": item}
