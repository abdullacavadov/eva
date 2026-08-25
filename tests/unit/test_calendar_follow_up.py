import pytest

from core.calendar_follow_up import build_calendar_follow_up, execute_calendar_follow_up
from core.result_resolver import FollowUpAction, ResultResolutionError


def _item():
    return {
        "id": "calendar_event:e1",
        "google_event_id": "e1",
        "calendar_id": "primary",
        "title": "Görüş",
        "start": "2026-08-25T15:00:00+04:00",
        "end": "2026-08-25T16:00:00+04:00",
        "all_day": False,
    }


def test_calendar_show_builds_read_dispatch():
    dispatch = build_calendar_follow_up(FollowUpAction("ikincini", "show", _item(), "göstər"))
    assert dispatch["tool_name"] == "read_calendar_event"
    assert dispatch["args"]["event_id"] == "e1"


def test_calendar_update_moves_event_to_tomorrow_preserving_time():
    dispatch = build_calendar_follow_up(FollowUpAction("bunu", "update", _item(), "sabaha keçir"))
    assert dispatch["tool_name"] == "update_calendar_event_by_id"
    assert dispatch["args"]["start_iso"] == "2026-08-26T15:00:00+04:00"
    assert dispatch["args"]["end_iso"] == "2026-08-26T16:00:00+04:00"


def test_calendar_delete_requires_confirmation():
    dispatch = build_calendar_follow_up(FollowUpAction("onu", "delete", _item(), "sil"))
    assert dispatch["confirmation_required"] is True
    result = execute_calendar_follow_up(dispatch)
    assert result["status"] == "confirmation_required"


def test_calendar_update_rejects_unsupported_mutation():
    with pytest.raises(ResultResolutionError):
        build_calendar_follow_up(FollowUpAction("bunu", "update", _item(), "başlığını dəyiş"))
