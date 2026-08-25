import pytest

from core.result_resolver import FollowUpAction, ResultResolutionError
from core.tool_executor import build_follow_up_dispatch


def _action(action, item=None):
    return FollowUpAction(
        reference="onu",
        action=action,
        item=item or {"id": "task:t2", "google_task_id": "t2", "task_list_id": "list1", "title": "İkinci task"},
    )


def test_dispatch_complete_maps_task_identity():
    dispatch = build_follow_up_dispatch(_action("complete"))

    assert dispatch.tool_name == "complete_reminder"
    assert dispatch.args == {"task_id": "t2", "list_name": "list1"}
    assert dispatch.confirmation_required is False


def test_dispatch_delete_requires_confirmation():
    dispatch = build_follow_up_dispatch(_action("delete"))

    assert dispatch.tool_name == "delete_reminder"
    assert dispatch.args == {"task_id": "t2", "list_name": "list1"}
    assert dispatch.confirmation_required is True


def test_dispatch_show_returns_target_without_tool_call():
    item = {"id": "task:t2", "title": "İkinci task"}
    dispatch = build_follow_up_dispatch(_action("show", item))

    assert dispatch.tool_name is None
    assert dispatch.args == {}
    assert dispatch.item == item
    assert dispatch.confirmation_required is False


def test_dispatch_update_requires_explicit_update_payload():
    with pytest.raises(ResultResolutionError, match="yeniləmə"):
        build_follow_up_dispatch(_action("update"))


def test_dispatch_rejects_unsupported_entity():
    with pytest.raises(ResultResolutionError, match="entity"):
        build_follow_up_dispatch(
            _action("complete", {"id": "email:m2", "subject": "Email"})
        )
