from datetime import datetime

import pytest

from core.follow_up_mutation import build_follow_up_mutation
from core.result_resolver import FollowUpAction, ResultResolutionError


def test_update_tomorrow_builds_timezone_aware_due_iso():
    now = datetime.fromisoformat("2026-08-25T15:30:00+04:00")
    action = FollowUpAction(
        reference="bunu",
        action="update",
        item={"id": "task:t1", "title": "Task"},
        action_text="sabaha keçir",
    )

    mutation = build_follow_up_mutation(action, now=now)

    assert mutation.fields == {"due_iso": "2026-08-26T09:00:00+04:00"}


def test_update_rejects_unsupported_mutation_text():
    action = FollowUpAction(
        reference="bunu",
        action="update",
        item={"id": "task:t1", "title": "Task"},
        action_text="gələn həftəyə keçir",
    )

    with pytest.raises(ResultResolutionError, match="dəstəklənən dəyişiklik"):
        build_follow_up_mutation(action)


def test_update_rejects_non_task_target():
    action = FollowUpAction(
        reference="bunu",
        action="update",
        item={"id": "email:m1", "subject": "Mail"},
        action_text="sabaha keçir",
    )

    with pytest.raises(ResultResolutionError, match="yalnız task"):
        build_follow_up_mutation(action)
