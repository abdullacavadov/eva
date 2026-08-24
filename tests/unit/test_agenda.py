from unittest.mock import patch

from actions.agenda import add_agenda_item, delete_agenda_item, get_daily_agenda


def test_add_agenda_item_requires_storage_choice():
    result = add_agenda_item("Call Ahmed")
    assert result["status"] == "needs_input"
    assert "Google Tasks" in result["meta"]["message"]
    assert "memory" in result["meta"]["choices"]
    assert "microsoft_todo" not in result["meta"]["choices"]


def test_add_memory_agenda_item():
    with patch("actions.agenda.update_memory") as update:
        result = add_agenda_item("Buy milk", storage="memory", due_iso="2026-08-24")
    update.assert_called_once()
    assert result["status"] == "success"
    assert result["data"][0]["source"] == "memory"


def test_google_tasks_falls_back_to_memory_when_unavailable():
    with patch("actions.agenda.add_reminder", return_value={"status": "error", "meta": {"message": "OAuth unavailable"}}), patch("actions.agenda.update_memory"):
        result = add_agenda_item("Prepare report", storage="google_tasks")
    assert result["status"] == "success"
    assert result["data"][0]["source"] == "memory"
    assert result["meta"]["fallback"] == "memory"


def test_daily_agenda_has_flat_structured_data_and_source_groups():
    with patch("actions.agenda.get_calendar_events", return_value={"status": "success", "data": [{"id": "calendar_event:1", "title": "Meeting"}]}), patch("actions.agenda.get_reminders", return_value={"status": "success", "data": [{"id": "task:1", "title": "Call"}]}), patch("actions.agenda._memory_items", return_value=[{"id": "memory:1", "title": "Note", "due": "2026-08-24", "source": "memory"}]):
        result = get_daily_agenda()
    assert result["status"] == "success"
    assert {item["source"] for item in result["data"] if "source" in item} >= {"memory"}
    assert "calendar" in result["meta"]["groups"]
    assert "tasks" in result["meta"]["groups"]
    assert "memory" in result["meta"]["groups"]


def test_delete_requires_confirmation():
    with patch("actions.agenda._memory_items", return_value=[{"id": "memory:1", "title": "Delete this", "source": "memory"}]):
        result = delete_agenda_item("Delete this")
    assert result["status"] == "needs_confirmation"
    assert result["meta"]["confirmation_required"] is True
