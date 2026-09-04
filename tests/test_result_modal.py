from datetime import datetime, timedelta, timezone

from core.result_context import ResultContext
from core.result_modal import format_result_for_modal
from core.result_resolver import resolve_follow_up_action


def _context():
    now = datetime.now(timezone.utc)
    return ResultContext(
        result_id="r_test",
        type="calendar",
        query={"intent": "lookup", "period": "today"},
        data=[
            {"id": "calendar:1", "title": "Komanda görüşü", "start_iso": "2026-09-05T10:00:00+04:00"},
            {"id": "calendar:2", "title": "Layihə görüşü", "start_iso": "2026-09-05T14:00:00+04:00"},
        ],
        count=2,
        created_at=now,
        expires_at=now + timedelta(minutes=30),
    )


def test_goster_baxim_resolves_to_current_result_show():
    context = _context()
    action = resolve_follow_up_action(context, "göstər baxım")
    assert action.reference == "current"
    assert action.action == "show"
    assert action.item["id"] == "calendar:1"


def test_goster_baxim_ascii_variant_is_supported():
    action = resolve_follow_up_action(_context(), "goster baxim")
    assert action.reference == "current"
    assert action.action == "show"


def test_modal_formatter_contains_all_current_result_items():
    text = format_result_for_modal(_context())
    assert "MƏNBƏ: CALENDAR" in text
    assert "NƏTİCƏ SAYI: 2" in text
    assert "Komanda görüşü" in text
    assert "Layihə görüşü" in text
    assert "2026-09-05T14:00:00+04:00" in text


def test_modal_formatter_can_show_selected_item_only():
    context = _context()
    text = format_result_for_modal(context, context.data[1])
    assert "Layihə görüşü" in text
    assert "Komanda görüşü" not in text
