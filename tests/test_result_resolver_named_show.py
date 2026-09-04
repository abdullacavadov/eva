from datetime import datetime, timedelta, timezone

from core.result_context import ResultContext
from core.result_resolver import resolve_follow_up_action


def _context():
    now = datetime.now(timezone.utc)
    return ResultContext(
        result_id="r_test",
        type="calendar_event",
        query="this weekend",
        data=[
            {"id": "calendar:1", "title": "Ev Partisi", "start": "2026-09-05T20:00:00+04:00"},
            {"id": "calendar:2", "title": "İş görüşməsi", "start": "2026-09-06T10:00:00+04:00"},
        ],
        count=2,
        created_at=now,
        expires_at=now + timedelta(minutes=30),
    )


def test_named_item_show_follow_up_resolves_item():
    action = resolve_follow_up_action(_context(), "Həmin partini göstər baxım")
    assert action.action == "show"
    assert action.item["title"] == "Ev Partisi"


def test_named_item_show_follow_up_without_demonstrative_resolves_item():
    action = resolve_follow_up_action(_context(), "Ev partisini göstər")
    assert action.action == "show"
    assert action.item["title"] == "Ev Partisi"


def test_modal_display_mode_uses_current_result():
    action = resolve_follow_up_action(_context(), "modalda göstər")
    assert action.action == "show"
    assert action.reference == "current"
    assert action.item["title"] == "Ev Partisi"


def test_screen_display_mode_uses_current_result():
    action = resolve_follow_up_action(_context(), "bunu ekranda göstər")
    assert action.action == "show"
    assert action.reference == "current"
    assert action.item["title"] == "Ev Partisi"
