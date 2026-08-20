from unittest.mock import patch

from actions.calendar import get_calendar_events
from actions.reminders import get_reminders


def test_calendar_result_is_structured():
    events = [{
        "id": "event-1",
        "summary": "Dentist",
        "start": {"dateTime": "2026-08-20T10:00:00+04:00"},
        "end": {"dateTime": "2026-08-20T11:00:00+04:00"},
        "location": "Clinic",
    }]
    with patch("actions.calendar.list_events", return_value=events):
        result = get_calendar_events("today", 6)
    assert result["type"] == "calendar_event"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "calendar_event:event-1"
    assert result["data"][0]["google_event_id"] == "event-1"
    assert result["data"][0]["title"] == "Dentist"


def test_calendar_empty_result():
    with patch("actions.calendar.list_events", return_value=[]):
        result = get_calendar_events("today", 6)
    assert result["type"] == "calendar_event"
    assert result["status"] == "empty"
    assert result["data"] == []


def test_tasks_result_is_structured():
    tasks = [{
        "id": "task-1",
        "title": "Call dentist",
        "due": "2026-08-20T12:00:00Z",
        "notes": "Ask about appointment",
        "status": "needsAction",
    }]
    with patch("actions.reminders.resolve_task_list_id", return_value="list-1"), \
         patch("actions.reminders.list_tasks", return_value=tasks):
        result = get_reminders("upcoming", 8, "")
    assert result["type"] == "task"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "task:task-1"
    assert result["data"][0]["google_task_id"] == "task-1"


def test_tasks_empty_result():
    with patch("actions.reminders.resolve_task_list_id", return_value="list-1"), \
         patch("actions.reminders.list_tasks", return_value=[]):
        result = get_reminders("upcoming", 8, "")
    assert result["type"] == "task"
    assert result["status"] == "empty"
    assert result["count"] == 0
