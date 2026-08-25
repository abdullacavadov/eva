from actions.daily_report import build_daily_report


def test_daily_report_returns_short_prioritized_highlights():
    result = build_daily_report({
        "calendar": {"status": "success", "type": "calendar_event", "data": [{"id": "calendar:1", "title": "Team meeting", "date": "2026-08-25T10:00:00"}]},
        "tasks": {"status": "success", "type": "task", "data": [{"id": "task:1", "title": "Urgent report deadline", "due": "2026-08-25"}]},
        "memory": {"status": "success", "type": "memory", "data": [{"id": "memory:1", "title": "Dinner with father"}]},
        "gmail": {"status": "success", "type": "email", "data": [{"id": "email:1", "subject": "Important client email", "snippet": "Please review"}]},
        "whatsapp": {"status": "success", "type": "whatsapp_message", "data": [{"id": "whatsapp:1", "title": "Ahmed", "snippet": "See you later"}]},
    }, "2026-08-25")
    assert result["status"] == "success"
    assert result["type"] == "daily_report"
    assert result["meta"]["total_items"] == 5
    assert len(result["data"]) == 5
    assert result["data"][0]["priority"] == 3
    assert {section["source"] for section in result["meta"]["sections"]} == {"calendar", "tasks", "memory", "gmail", "whatsapp"}


def test_daily_report_keeps_source_errors_without_failing_other_sources():
    result = build_daily_report({
        "calendar": {"status": "error", "data": [], "meta": {"message": "Calendar unavailable"}},
        "tasks": {"status": "success", "type": "task", "data": [{"id": "task:1", "title": "Call"}]},
    }, "2026-08-25")
    assert result["status"] == "success"
    assert result["meta"]["errors"]["calendar"] == "Calendar unavailable"
    assert result["data"][0]["source"] == "tasks"


def test_daily_report_empty_when_all_sources_fail():
    result = build_daily_report({
        "gmail": {"status": "error", "data": [], "meta": {"message": "Gmail unavailable"}},
        "whatsapp": {"status": "error", "data": [], "meta": {"message": "WhatsApp unavailable"}},
    }, "2026-08-25")
    assert result["status"] == "empty"
    assert result["type"] == "daily_report"
    assert set(result["meta"]["errors"]) == {"gmail", "whatsapp"}


def test_daily_report_builds_user_facing_summary_and_unread_whatsapp_count():
    result = build_daily_report({
        "calendar": {"status": "success", "data": [{"id": "c1", "title": "Meeting", "date": "2026-08-25T10:00:00"}]},
        "tasks": {"status": "success", "data": [{"id": "t1", "title": "Call", "due": "2026-08-25"}, {"id": "t2", "title": "Buy milk"}]},
        "gmail": {"status": "success", "data": [{"id": "g1", "subject": "Important invoice"}]},
        "whatsapp": {"status": "success", "data": [{"id": "w1", "title": "Ahmed", "unread_count": 2}, {"id": "w2", "title": "Family", "unread_count": 3}]},
        "memory": {"status": "success", "data": [{"id": "m1", "title": "Remember this"}]},
    }, "2026-08-25")
    assert result["meta"]["unread_whatsapp"] == 5
    assert "1 təqvim hadisəsi" in result["meta"]["summary_text"]
    assert "2 task" in result["meta"]["summary_text"]
    assert "1 email" in result["meta"]["summary_text"]
    assert "5 oxunmamış WhatsApp mesajı" in result["meta"]["summary_text"]
    assert "1 yaddaş qeydi" in result["meta"]["summary_text"]


def test_daily_report_marks_partial_source_failure_in_summary():
    result = build_daily_report({
        "calendar": {"status": "success", "data": [{"id": "c1", "title": "Meeting"}]},
        "gmail": {"status": "error", "data": [], "meta": {"message": "Gmail unavailable"}},
    }, "2026-08-25")
    assert "Bəzi mənbələr əlçatan olmadı." in result["meta"]["summary_text"]
