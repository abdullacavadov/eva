from actions.daily_report import build_daily_report


def test_daily_report_returns_short_prioritized_highlights():
    result = build_daily_report(
        {
            "calendar": {"status": "success", "type": "calendar_event", "data": [{"id": "calendar:1", "title": "Team meeting", "date": "2026-08-25T10:00:00"}]},
            "tasks": {"status": "success", "type": "task", "data": [{"id": "task:1", "title": "Urgent report deadline", "due": "2026-08-25"}]},
            "memory": {"status": "success", "type": "memory", "data": [{"id": "memory:1", "title": "Dinner with father"}]},
            "gmail": {"status": "success", "type": "email", "data": [{"id": "email:1", "subject": "Important client email", "snippet": "Please review"}]},
            "whatsapp": {"status": "success", "type": "whatsapp_message", "data": [{"id": "whatsapp:1", "title": "Ahmed", "snippet": "See you later"}]},
        },
        "2026-08-25",
    )
    assert result["status"] == "success"
    assert result["type"] == "daily_report"
    assert result["meta"]["total_items"] == 5
    assert len(result["data"]) == 5
    assert result["data"][0]["priority"] == 3
    assert {section["source"] for section in result["meta"]["sections"]} == {"calendar", "tasks", "memory", "gmail", "whatsapp"}


def test_daily_report_keeps_source_errors_without_failing_other_sources():
    result = build_daily_report(
        {
            "calendar": {"status": "error", "data": [], "meta": {"message": "Calendar unavailable"}},
            "tasks": {"status": "success", "type": "task", "data": [{"id": "task:1", "title": "Call"}]},
        },
        "2026-08-25",
    )
    assert result["status"] == "success"
    assert result["meta"]["errors"]["calendar"] == "Calendar unavailable"
    assert result["data"][0]["source"] == "tasks"


def test_daily_report_empty_when_all_sources_fail():
    result = build_daily_report(
        {
            "gmail": {"status": "error", "data": [], "meta": {"message": "Gmail unavailable"}},
            "whatsapp": {"status": "error", "data": [], "meta": {"message": "WhatsApp unavailable"}},
        },
        "2026-08-25",
    )
    assert result["status"] == "empty"
    assert result["type"] == "daily_report"
    assert set(result["meta"]["errors"]) == {"gmail", "whatsapp"}
