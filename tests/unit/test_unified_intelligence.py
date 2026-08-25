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


def test_cross_source_search_selects_calendar_tasks_memory():
    plan = plan_query("Marketə getməyi nə vaxt planlaşdırmışdım?")
    assert plan.intent == "cross_source_search"
    assert plan.sources == ("calendar", "tasks", "memory")


def test_contact_history_selects_whatsapp_and_memory():
    plan = plan_query("Əhmədlə bağlı son nə danışmışıq?")
    assert plan.intent == "contact_history"
    assert plan.sources == ("whatsapp", "memory")


def test_deletion_is_confirmation_protected_and_source_ambiguous():
    plan = plan_query("Marketə getməyi sil")
    assert plan.intent == "deletion"
    assert plan.needs_confirmation is True
    assert plan.metadata["ambiguous_source"] == "true"


def test_unified_result_preserves_source_and_structured_shape():
    calendar = {"status": "success", "type": "calendar", "data": [{"id": "calendar:1", "title": "Meeting", "start": "2026-08-25T10:00"}]}
    tasks = {"status": "success", "type": "task", "data": [{"id": "task:1", "title": "Call", "due": "2026-08-25"}]}
    with patch("core.orchestrator.get_calendar_events", return_value=calendar), patch("core.orchestrator.getattr", create=True), patch("actions.reminders.get_reminders", return_value=tasks), patch("core.orchestrator.load_memory", return_value={"agenda": {}}):
        result = execute_unified_query("Bu gün nə işim var?")
    assert result["type"] == "unified_query"
    assert result["status"] == "success"
    assert {item["source"] for item in result["data"]} >= {"calendar", "tasks"}
    assert result["query"]["sources"] == ["calendar", "tasks", "memory"]
