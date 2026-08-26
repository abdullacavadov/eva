from datetime import datetime, timedelta

import actions.reminder_memory as reminders


def test_reminder_is_stored_separately_and_counted_for_today(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "REMINDER_FILE", tmp_path / "reminders.json")
    due = datetime.now().astimezone().replace(hour=18, minute=0, second=0, microsecond=0).isoformat()

    created = reminders.add_reminder("Kommunal ödənişi xatırla", due)
    assert created["status"] == "success"
    reminder_id = created["data"][0]["id"]

    result = reminders.get_reminders("today")
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == reminder_id
    assert result["data"][0]["type"] == "reminder"
    assert result["data"][0]["source"] == "eva_memory"
    assert reminders.REMINDER_FILE.exists()


def test_completed_reminder_is_not_counted_as_open(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "REMINDER_FILE", tmp_path / "reminders.json")
    due = datetime.now().astimezone().replace(hour=19, minute=0, second=0, microsecond=0).isoformat()

    created = reminders.add_reminder("Açıq reminder", due)
    reminder_id = created["data"][0]["id"]
    assert reminders.complete_reminder(reminder_id)["status"] == "success"

    assert reminders.get_reminders("today")["status"] == "empty"
    assert reminders.get_reminders("today", include_completed=True)["count"] == 1


def test_reminder_due_on_another_day_is_not_counted_today(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "REMINDER_FILE", tmp_path / "reminders.json")
    tomorrow = (datetime.now().astimezone() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()

    reminders.add_reminder("Sabahkı reminder", tomorrow)

    assert reminders.get_reminders("today")["status"] == "empty"
    assert reminders.get_reminders("upcoming")["count"] == 1
