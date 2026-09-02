import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.tool_executor import ToolExecutor


def make_executor():
    ui = MagicMock(); ui.muted = False
    return ToolExecutor(ui, MagicMock(), MagicMock(), MagicMock())


def test_risky_calendar_action_requires_confirmation_before_side_effect():
    executor = make_executor()
    fc = SimpleNamespace(id="c1", name="delete_calendar_event", args={"title": "Test"})
    with patch("core.tool_executor.delete_calendar_event") as delete:
        response = asyncio.run(executor.execute(fc))
    assert response.response["result"]["status"] == "needs_confirmation"
    assert response.response["result"]["meta"]["confirmation_id"]
    delete.assert_not_called()


def test_confirmation_executes_exact_pending_calendar_action_once():
    executor = make_executor()
    with patch("core.tool_executor.delete_calendar_event", return_value="deleted") as delete:
        first = asyncio.run(executor.execute(SimpleNamespace(id="c1", name="delete_calendar_event", args={"title": "Test", "start_iso": "2026-09-02T10:00:00"})))
        token = first.response["result"]["meta"]["confirmation_id"]
        second = asyncio.run(executor.execute(SimpleNamespace(id="c2", name="confirm_action", args={"confirmation_id": token})))
    assert second.response["result"] == "deleted"
    delete.assert_called_once_with("Test", "2026-09-02T10:00:00", "", False)


def test_eva_reminder_is_separate_from_google_tasks(monkeypatch):
    import actions.eva_reminders as reminders
    memory = {}
    monkeypatch.setattr(reminders, "load_memory", lambda: memory)
    monkeypatch.setattr(reminders, "update_memory", lambda value: memory.update(value))
    monkeypatch.setattr(reminders, "_write_memory", lambda value: memory.clear() or memory.update(value))
    created = reminders.add_eva_reminder("Vergi ödə", "2026-09-03T09:00:00+04:00")
    assert created["data"][0]["source"] == "eva_memory"
    assert "eva_reminders" in memory
    assert reminders.get_eva_reminders("upcoming")["count"] == 1


def test_meta_whatsapp_action_is_confirmation_gated():
    executor = make_executor()
    fc = SimpleNamespace(id="w1", name="send_whatsapp_business_message", args={"phone_number": "+994501112233", "message": "Salam"})
    with patch("core.tool_executor.send_whatsapp_business_message") as send:
        response = asyncio.run(executor.execute(fc))
    assert response.response["result"]["status"] == "needs_confirmation"
    send.assert_not_called()
