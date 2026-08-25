from __future__ import annotations

from datetime import datetime, timezone

from core.proactive import NotificationPolicy, ProactiveEngine, ProactiveScheduler


def _now(hour: int = 12) -> datetime:
    return datetime(2026, 8, 25, hour, 0, tzinfo=timezone.utc)


def test_quiet_hours_suppress_notifications():
    policy = NotificationPolicy(quiet_start="23:00", quiet_end="07:00")
    pending = {"gmail:1": {"key": "gmail:1", "source": "gmail", "item": {"subject": "Test"}}}
    assert policy.choose(pending, {}, _now(2)) == []


def test_rate_limit_caps_notifications_per_hour():
    policy = NotificationPolicy(rate_limit=2, quiet_start="00:00", quiet_end="00:01")
    pending = {
        f"gmail:{index}": {"key": f"gmail:{index}", "source": "gmail", "item": {"subject": str(index)}}
        for index in range(5)
    }
    history = {"old-1": _now(11).isoformat()}
    assert len(policy.choose(pending, history, _now(12))) == 1


def test_calendar_policy_requires_nearby_event():
    policy = NotificationPolicy(quiet_start="00:00", quiet_end="00:01")
    pending = {
        "calendar:1": {"key": "calendar:1", "source": "calendar", "item": {"title": "Meeting", "start": "2026-08-25T13:00:00+00:00"}},
        "calendar:2": {"key": "calendar:2", "source": "calendar", "item": {"title": "Later", "start": "2026-08-27T13:00:00+00:00"}},
    }
    selected = policy.choose(pending, {}, _now(12))
    assert [item["key"] for item in selected] == ["calendar:1"]


def test_task_policy_requires_due_within_24_hours():
    policy = NotificationPolicy(quiet_start="00:00", quiet_end="00:01")
    pending = {
        "tasks:1": {"key": "tasks:1", "source": "tasks", "item": {"title": "Today", "due": "2026-08-26T10:00:00+00:00"}},
        "tasks:2": {"key": "tasks:2", "source": "tasks", "item": {"title": "Later", "due": "2026-08-28T10:00:00+00:00"}},
    }
    selected = policy.choose(pending, {}, _now(12))
    assert [item["key"] for item in selected] == ["tasks:1"]


def test_engine_first_poll_only_creates_baseline(tmp_path, monkeypatch):
    engine = ProactiveEngine(tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [{"id": "1", "subject": "Existing"}], "whatsapp": [], "calendar": [], "tasks": [], "memory": {"notes": []}})
    assert engine.poll(_now(12)) == []
    assert (tmp_path / "state.json").exists()


def test_engine_detects_new_gmail_after_baseline(tmp_path, monkeypatch):
    engine = ProactiveEngine(tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    values = [[{"id": "1", "subject": "Existing"}], [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "New"}]]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": values.pop(0), "whatsapp": [], "calendar": [], "tasks": [], "memory": {}})
    assert engine.poll(_now(12)) == []
    events = engine.poll(_now(12))
    assert len(events) == 1
    assert events[0]["source"] == "gmail"
    assert "New" in events[0]["text"]


def test_engine_does_not_repeat_same_notification(tmp_path, monkeypatch):
    engine = ProactiveEngine(tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    values = [
        [{"id": "1", "subject": "Existing"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "New"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "New"}],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": values.pop(0), "whatsapp": [], "calendar": [], "tasks": [], "memory": {}})
    engine.poll(_now(12))
    assert len(engine.poll(_now(12))) == 1
    assert engine.poll(_now(12)) == []


def test_engine_keeps_quiet_hour_event_pending(tmp_path, monkeypatch):
    engine = ProactiveEngine(tmp_path / "state.json", NotificationPolicy(quiet_start="23:00", quiet_end="07:00"))
    values = [
        [{"id": "1", "subject": "Existing"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "Night"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "Night"}],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": values.pop(0), "whatsapp": [], "calendar": [], "tasks": [], "memory": {}})
    engine.poll(_now(12))
    assert engine.poll(_now(2)) == []
    events = engine.poll(_now(8))
    assert len(events) == 1


def test_whatsapp_read_state_does_not_trigger_notification(tmp_path, monkeypatch):
    engine = ProactiveEngine(tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    values = [
        [{"conversation_id": "c1", "title": "Ali", "unread_count": 2}],
        [{"conversation_id": "c1", "title": "Ali", "unread_count": 0}],
        [{"conversation_id": "c1", "title": "Ali", "unread_count": 1}],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [], "whatsapp": values.pop(0), "calendar": [], "tasks": [], "memory": {}})
    assert engine.poll(_now(12)) == []
    assert engine.poll(_now(12)) == []
    events = engine.poll(_now(12))
    assert len(events) == 1
    assert events[0]["source"] == "whatsapp"


def test_scheduler_poll_once_forwards_notifications():
    received = []

    class FakeEngine:
        def poll(self):
            return [{"key": "gmail:1", "text": "Yeni email"}]

    scheduler = ProactiveScheduler(FakeEngine(), received.append, interval=10)
    events = scheduler.poll_once()
    assert events[0]["key"] == "gmail:1"
    assert received == events
