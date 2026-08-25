from unittest.mock import patch

from core.query_planner import plan_query
from core.orchestrator import execute_unified_query, execute_unified_deletion


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


def test_unified_deletion_requires_explicit_confirmation():
    tasks = {
        "status": "success",
        "type": "task",
        "data": [{"id": "google-1", "google_task_id": "google-1", "task_list_id": "list-1", "title": "Marketə get"}],
    }
    with patch("actions.reminders.get_reminders", return_value=tasks), patch("core.orchestrator.get_calendar_events", return_value={"status": "empty", "data": []}), patch("core.orchestrator.load_memory", return_value={"agenda": {}}), patch("actions.reminders.delete_reminder") as delete_mock:
        result = execute_unified_deletion("Market taskını sil")

    assert result["meta"]["requires_confirmation"] is True
    assert result["meta"]["deletion_safe"] is True
    assert result["meta"]["selected_id"] is None
    delete_mock.assert_not_called()


def test_unified_task_deletion_deletes_only_selected_candidate_after_confirmation():
    tasks = {
        "status": "success",
        "type": "task",
        "data": [
            {"id": "google-1", "google_task_id": "google-1", "task_list_id": "list-1", "title": "Marketə get"},
            {"id": "google-2", "google_task_id": "google-2", "task_list_id": "list-1", "title": "Marketdən süd al"},
        ],
    }
    with patch("actions.reminders.get_reminders", return_value=tasks), patch("core.orchestrator.get_calendar_events", return_value={"status": "empty", "data": []}), patch("core.orchestrator.load_memory", return_value={"agenda": {}}), patch("actions.reminders.delete_reminder", return_value={"status": "success", "type": "task", "data": []}) as delete_mock:
        candidates = execute_unified_deletion("Market taskını sil")
        selected_id = candidates["data"][0]["id"]
        result = execute_unified_deletion("Market taskını sil", selected_id=selected_id, confirmed=True)

    assert result["meta"]["deleted"] is True
    assert result["meta"]["selected_id"] == selected_id
    delete_mock.assert_called_once_with("google-1", "list-1")


def test_unified_memory_deletion_deletes_selected_memory_record_after_confirmation():
    memory = {"agenda": {"market": {"title": "Market", "value": "Marketə get", "type": "task"}}}
    with patch("core.orchestrator.load_memory", return_value=memory), patch("core.orchestrator.delete_memory", return_value="agenda/market yaddaşdan silindi.") as delete_mock, patch("core.orchestrator.get_calendar_events", return_value={"status": "empty", "data": []}), patch("actions.reminders.get_reminders", return_value={"status": "empty", "data": []}):
        candidates = execute_unified_deletion("Market qeydini sil")
        selected_id = candidates["data"][0]["id"]
        result = execute_unified_deletion("Market qeydini sil", selected_id=selected_id, confirmed=True)

    assert result["meta"]["deleted"] is True
    delete_mock.assert_called_once_with(category="agenda", key="market")


def test_unified_calendar_deletion_deletes_selected_event_after_confirmation():
    calendar = {
        "status": "success",
        "type": "calendar_event",
        "data": [{"id": "event-1", "title": "Market görüşü", "start": "2026-08-26T10:00"}],
    }
    with patch("core.orchestrator.get_calendar_events", return_value=calendar), patch("actions.reminders.get_reminders", return_value={"status": "empty", "data": []}), patch("core.orchestrator.load_memory", return_value={"agenda": {}}), patch("core.orchestrator.delete_calendar_event", return_value={"status": "success", "type": "calendar_event", "data": []}) as delete_mock:
        candidates = execute_unified_deletion("Market görüşünü sil")
        selected_id = candidates["data"][0]["id"]
        result = execute_unified_deletion("Market görüşünü sil", selected_id=selected_id, confirmed=True)

    assert result["meta"]["deleted"] is True
    delete_mock.assert_called_once_with("Market görüşü", "2026-08-26T10:00")


def test_unified_deletion_rejects_unselected_id_without_deleting():
    tasks = {
        "status": "success",
        "type": "task",
        "data": [{"id": "google-1", "google_task_id": "google-1", "task_list_id": "list-1", "title": "Marketə get"}],
    }
    with patch("actions.reminders.get_reminders", return_value=tasks), patch("core.orchestrator.get_calendar_events", return_value={"status": "empty", "data": []}), patch("core.orchestrator.load_memory", return_value={"agenda": {}}), patch("actions.reminders.delete_reminder") as delete_mock:
        result = execute_unified_deletion("Market taskını sil", selected_id="task:does-not-exist", confirmed=True)

    assert result["meta"]["deleted"] is not True
    assert result["meta"]["requires_confirmation"] is True
    delete_mock.assert_not_called()
