from unittest.mock import patch

from core.query_planner import plan_query
from core.orchestrator import execute_unified_query


def test_daily_agenda_query_selects_calendar_tasks_memory():
    plan = plan_query("Bu gün nə işim var?")
    assert plan.intent == "agenda_query"
    assert plan.period == "today"
    assert plan.sources == ("calendar", "tasks", "memory")


def test_daily_report_selects_all_report_sources():
    plan = plan_query("Bu gün nə baş verib?")
    assert plan.intent == "daily_report"
    assert plan.sources == ("gmail", "whatsapp", "calendar", "tasks", "memory")


def test_daily_report_accepts_report_request_phrase():
    plan = plan_query("Bu gün üçün report ver")
    assert plan.intent == "daily_report"
    assert plan.period == "today"
    assert plan.sources == ("gmail", "whatsapp", "calendar", "tasks", "memory")


def test_cross_source_search_selects_calendar_tasks_memory():
    plan = plan_query("Marketə getməyi nə vaxt planlaşdırmışdım?")
    assert plan.intent == "cross_source_search"
    assert plan.sources == ("calendar", "tasks", "memory")
    assert plan.search_text == "Marketə getməyi"
    assert plan.metadata["entity"] == "Marketə getməyi"


def test_contact_history_selects_whatsapp_and_memory():
    plan = plan_query("Əhmədlə bağlı son nə danışmışıq?")
    assert plan.intent == "contact_history"
    assert plan.sources == ("whatsapp", "memory")
    assert plan.metadata["entity"] == "Əhməd"


def test_mixed_person_and_tomorrow_query_selects_calendar_whatsapp_memory():
    plan = plan_query("Sabah Əhmədlə görüşüm var?")
    assert plan.intent == "cross_source_search"
    assert plan.period == "tomorrow"
    assert plan.sources == ("calendar", "whatsapp", "memory")
    assert plan.search_text == "Əhməd"


def test_cross_source_query_filters_calendar_and_tasks_by_entity():
    calendar = {
        "status": "success",
        "type": "calendar_event",
        "data": [
            {"id": "calendar:ahmed", "title": "Əhmədlə görüş", "start": "2026-08-26T10:00"},
            {"id": "calendar:other", "title": "Komanda görüşü", "start": "2026-08-26T12:00"},
        ],
    }
    tasks = {
        "status": "success",
        "type": "task",
        "data": [
            {"id": "task:ahmed", "title": "Əhmədə sənədləri göndər", "due": "2026-08-26"},
            {"id": "task:other", "title": "Marketə get", "due": "2026-08-26"},
        ],
    }
    with patch("core.orchestrator.get_calendar_events", return_value=calendar), patch("actions.reminders.get_reminders", return_value=tasks), patch("core.orchestrator.load_memory", return_value={"agenda": {}}):
        result = execute_unified_query("Sabah Əhmədlə görüşüm var?")

    assert result["status"] == "success"
    assert {item["id"] for item in result["data"]} == {"calendar:ahmed", "task:ahmed"}
    assert result["meta"]["entity"] == "Əhməd"


def test_cross_source_result_does_not_include_unrelated_memory():
    memory = {
        "agenda": {
            "a": {"title": "Əhmədlə görüş", "value": "Əhmədlə görüş barədə danışdıq", "type": "note"},
            "b": {"title": "Market", "value": "Marketə getmək", "type": "task"},
        }
    }
    with patch("core.orchestrator.get_calendar_events", return_value={"status": "empty", "data": []}), patch("actions.reminders.get_reminders", return_value={"status": "empty", "data": []}), patch("core.orchestrator.load_memory", return_value=memory):
        result = execute_unified_query("Marketə getməyi nə vaxt planlaşdırmışdım?")

    assert result["status"] == "success"
    assert [item["title"] for item in result["data"]] == ["Market"]


def test_deletion_is_confirmation_protected_and_source_ambiguous():
    plan = plan_query("Marketə getməyi sil")
    assert plan.intent == "deletion"
    assert plan.needs_confirmation is True
    assert plan.metadata["ambiguous_source"] == "true"


def test_unified_result_preserves_source_and_structured_shape():
    calendar = {"status": "success", "type": "calendar", "data": [{"id": "calendar:1", "title": "Meeting", "start": "2026-08-25T10:00"}]}
    tasks = {"status": "success", "type": "task", "data": [{"id": "task:1", "title": "Call", "due": "2026-08-25"}]}
    with patch("core.orchestrator.get_calendar_events", return_value=calendar), patch("actions.reminders.get_reminders", return_value=tasks), patch("core.orchestrator.load_memory", return_value={"agenda": {}}):
        result = execute_unified_query("Bu gün nə işim var?")
    assert result["type"] == "unified_query"
    assert result["status"] == "success"
    assert {item["source"] for item in result["data"]} >= {"calendar", "tasks"}
    assert result["query"]["sources"] == ["calendar", "tasks", "memory"]
