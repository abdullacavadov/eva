import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from core.tool_executor import ToolExecutor


def _executor():
    ui = SimpleNamespace(muted=False, set_state=lambda *_: None, play_success_sfx=lambda: None)
    webcam = SimpleNamespace()
    return ToolExecutor(ui, webcam, lambda *_: None, lambda *_: None), ui


def test_create_contact_is_dispatched():
    executor, ui = _executor()
    fc = SimpleNamespace(id="contact-create-1", name="create_contact", args={"display_name": "Test", "phone_number": "+994501234567"})
    with patch("core.tool_executor.create_contact", return_value="Google kontaktı yaradıldı.") as mock_action:
        response = asyncio.run(executor.execute(fc))
    mock_action.assert_called_once_with("Test", "+994501234567")
    assert response.response["result"] == "Google kontaktı yaradıldı."


def test_update_contact_is_dispatched_with_resource_name():
    executor, _ = _executor()
    fc = SimpleNamespace(id="contact-update-1", name="update_contact", args={"resource_name": "people/c123", "display_name": "Updated", "phone_number": "+994559041494"})
    with patch("core.tool_executor.update_contact", return_value="Google kontaktı yeniləndi.") as mock_action:
        response = asyncio.run(executor.execute(fc))
    mock_action.assert_called_once_with("people/c123", "Updated", "+994559041494")
    assert response.response["result"] == "Google kontaktı yeniləndi."


def test_delete_contact_is_confirmation_gated():
    executor, _ = _executor()
    fc = SimpleNamespace(id="contact-delete-1", name="delete_contact", args={"resource_name": "people/c123"})
    with patch("core.tool_executor.delete_contact", return_value="Google kontaktı silindi.") as mock_action:
        response = asyncio.run(executor.execute(fc))
    mock_action.assert_not_called()
    assert response.response["type"] == "confirmation"
    assert response.response["status"] == "needs_confirmation"


def test_structured_action_result_is_saved_and_can_be_selected():
    executor, _ = _executor()
    fc = SimpleNamespace(id="calendar-1", name="get_calendar_events", args={"query": "2026-08-20", "limit": 6})
    structured = {"type": "calendar_event", "status": "success", "query": {"query": "2026-08-20"}, "data": [{"id": "calendar_event:e1", "summary": "Dentist", "google_event_id": "e1"}, {"id": "calendar_event:e2", "summary": "Meeting", "google_event_id": "e2"}], "count": 2, "selected": None, "meta": {}}
    with patch("core.tool_executor.get_calendar_events", return_value=structured):
        asyncio.run(executor.execute(fc))
    current = executor.result_store.current()
    assert current is not None
    assert current.type == "calendar_event"
    selected = executor.resolve_follow_up("Dentist")
    assert selected["id"] == "calendar_event:e1"
    assert executor.result_store.selected()["google_event_id"] == "e1"


def test_non_structured_action_result_is_not_saved():
    executor, _ = _executor()
    fc = SimpleNamespace(id="contact-plain-1", name="create_contact", args={"display_name": "Test", "phone_number": "+994501234567"})
    with patch("core.tool_executor.create_contact", return_value="Google kontaktı yaradıldı."):
        asyncio.run(executor.execute(fc))
    assert executor.result_store.current() is None
