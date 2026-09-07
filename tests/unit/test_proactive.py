from __future__ import annotations

from datetime import datetime, timezone

from core.proactive import NotificationPolicy, ProactiveEngine, ProactiveScheduler


def _now(hour: int = 12) -> datetime:
    return datetime(2026, 8, 25, hour, 0, tzinfo=timezone.utc)


def test_quiet_hours_suppress_notifications():
    policy = NotificationPolicy(quiet_start="23:00", quiet_end="07:00")
    pending = {"gmail:1": {"key": "gmail:1",
                           "source": "gmail", "item": {"subject": "Test"}}}
    assert policy.choose(pending, {}, _now(2)) == []


def test_rate_limit_caps_notifications_per_hour():
    policy = NotificationPolicy(
        rate_limit=2, quiet_start="00:00", quiet_end="00:01")
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
    engine = ProactiveEngine(
        tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [{"id": "1", "subject": "Existing"}], "whatsapp": [
    ], "calendar": [], "tasks": [], "memory": {"notes": []}})
    assert engine.poll(_now(12)) == []
    assert (tmp_path / "state.json").exists()


def test_engine_detects_new_gmail_after_baseline(tmp_path, monkeypatch):
    engine = ProactiveEngine(
        tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    values = [[{"id": "1", "subject": "Existing"}], [
        {"id": "1", "subject": "Existing"}, {"id": "2", "subject": "New"}]]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": values.pop(
        0), "whatsapp": [], "calendar": [], "tasks": [], "memory": {}})
    assert engine.poll(_now(12)) == []
    events = engine.poll(_now(12))
    assert len(events) == 1
    assert events[0]["source"] == "gmail"
    assert "New" in events[0]["text"]


def test_engine_does_not_repeat_same_notification(tmp_path, monkeypatch):
    engine = ProactiveEngine(
        tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    values = [
        [{"id": "1", "subject": "Existing"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "New"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "New"}],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": values.pop(
        0), "whatsapp": [], "calendar": [], "tasks": [], "memory": {}})
    engine.poll(_now(12))
    assert len(engine.poll(_now(12))) == 1
    assert engine.poll(_now(12)) == []


def test_engine_keeps_quiet_hour_event_pending(tmp_path, monkeypatch):
    engine = ProactiveEngine(
        tmp_path / "state.json", NotificationPolicy(quiet_start="23:00", quiet_end="07:00"))
    values = [
        [{"id": "1", "subject": "Existing"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "Night"}],
        [{"id": "1", "subject": "Existing"}, {"id": "2", "subject": "Night"}],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": values.pop(
        0), "whatsapp": [], "calendar": [], "tasks": [], "memory": {}})
    engine.poll(_now(12))
    assert engine.poll(_now(2)) == []
    events = engine.poll(_now(8))
    assert len(events) == 1


def test_whatsapp_read_state_does_not_trigger_notification(tmp_path, monkeypatch):
    engine = ProactiveEngine(
        tmp_path / "state.json", NotificationPolicy(quiet_start="00:00", quiet_end="00:01"))
    values = [
        [{"conversation_id": "c1", "title": "Ali", "unread_count": 2}],
        [{"conversation_id": "c1", "title": "Ali", "unread_count": 0}],
        [{"conversation_id": "c1", "title": "Ali", "unread_count": 1}],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: {
                        "gmail": [], "whatsapp": values.pop(0), "calendar": [], "tasks": [], "memory": {}})
    assert engine.poll(_now(12)) == []
    assert engine.poll(_now(12)) == []
    events = engine.poll(_now(12))
    assert len(events) == 1
    assert events[0]["source"] == "whatsapp"


def test_policy_orders_eligible_events_by_priority():
    policy = NotificationPolicy(quiet_start="00:00", quiet_end="00:01")
    pending = {
        "gmail:normal": {"key": "gmail:normal", "source": "gmail", "item": {"subject": "Newsletter"}},
        "gmail:urgent": {"key": "gmail:urgent", "source": "gmail", "item": {"subject": "URGENT: payment deadline"}},
        "calendar:near": {"key": "calendar:near", "source": "calendar", "item": {"title": "Meeting", "start": "2026-08-25T12:10:00+00:00"}},
    }
    selected = policy.choose(pending, {}, _now(12))
    assert [item["key"] for item in selected] == [
        "calendar:near", "gmail:urgent"]


def test_policy_priority_does_not_change_eligibility():
    policy = NotificationPolicy(
        rate_limit=2, quiet_start="00:00", quiet_end="00:01")
    pending = {
        "gmail:urgent": {"key": "gmail:urgent", "source": "gmail", "item": {"subject": "URGENT"}},
        "calendar:far": {"key": "calendar:far", "source": "calendar", "item": {"title": "Later", "start": "2026-08-27T12:00:00+00:00"}},
        "tasks:due": {"key": "tasks:due", "source": "tasks", "item": {"title": "Due", "due": "2026-08-25T11:00:00+00:00"}},
    }
    selected = policy.choose(pending, {}, _now(12))
    assert [item["key"] for item in selected] == ["tasks:due", "gmail:urgent"]


def test_policy_suppresses_gmail_newsletter_noise():
    policy = NotificationPolicy(quiet_start="00:00", quiet_end="00:01")
    pending = {
        "gmail:newsletter": {"key": "gmail:newsletter", "source": "gmail", "item": {"subject": "Weekly newsletter"}},
        "gmail:important": {"key": "gmail:important", "source": "gmail", "item": {"subject": "Client payment approval"}},
    }
    selected = policy.choose(pending, {}, _now(12))
    assert [item["key"] for item in selected] == ["gmail:important"]


def test_scheduler_poll_once_forwards_notifications():
    received = []

    class FakeEngine:
        def poll(self):
            return [{"key": "gmail:1", "text": "Yeni email"}]

    scheduler = ProactiveScheduler(FakeEngine(), received.append, interval=10)
    events = scheduler.poll_once()
    assert events[0]["key"] == "gmail:1"
    assert received == events


def test_scheduler_does_not_ack_failed_notification():
    class FakeEngine:
        def __init__(self):
            self.acked = []

        def poll(self):
            return [
                {
                    "key": "gmail:failed",
                    "source": "gmail",
                    "title": "Important email",
                }
            ]

        def acknowledge_notification(self, key):
            self.acked.append(key)

    engine = FakeEngine()

    scheduler = ProactiveScheduler(
        engine,
        lambda event: False,
    )

    events = scheduler.poll_once()

    assert events == []
    assert engine.acked == []


def test_scheduler_acks_successful_notification():
    class FakeEngine:
        def __init__(self):
            self.acked = []

        def poll(self):
            return [
                {
                    "key": "gmail:success",
                    "source": "gmail",
                    "title": "Important email",
                }
            ]

        def acknowledge_notification(self, key):
            self.acked.append(key)
            return True

    engine = FakeEngine()

    scheduler = ProactiveScheduler(
        engine,
        lambda event: True,
    )

    events = scheduler.poll_once()

    assert len(events) == 1
    assert engine.acked == ["gmail:success"]


def test_scheduler_does_not_ack_when_callback_raises():
    class FakeEngine:
        def __init__(self):
            self.acked = []

        def poll(self):
            return [
                {
                    "key": "gmail:exception",
                    "source": "gmail",
                    "title": "Important email",
                }
            ]

        def acknowledge_notification(self, key):
            self.acked.append(key)

    engine = FakeEngine()

    def failing_callback(event):
        raise RuntimeError("delivery failed")

    scheduler = ProactiveScheduler(
        engine,
        failing_callback,
    )

    events = scheduler.poll_once()

    assert events == []
    assert engine.acked == []


def test_failed_notification_can_be_retried_after_retry_window():
    from datetime import timedelta

    now = _now(12)

    event = {
        "key": "gmail:retry",
        "source": "gmail",
        "item": {"subject": "Retry me"},
        "_offered_at": (now - timedelta(minutes=2)).isoformat(),
    }

    policy = NotificationPolicy(
        quiet_start="00:00",
        quiet_end="00:01",
    )

    pending = {
        "gmail:retry": event,
    }

    selected = policy.choose(pending, {}, now)

    assert len(selected) == 1
    assert selected[0]["key"] == "gmail:retry"


def test_correlated_notification_acknowledges_all_children(tmp_path):
    state_file = tmp_path / "proactive-state.json"

    engine = ProactiveEngine(state_file)

    event = {
        "key": "calendar:primary",
        "source": "correlated",
        "title": "Payment deadline",
        "_correlated_keys": [
            "tasks:child",
            "gmail:child",
        ],
    }

    state = engine._load()

    state["pending"] = {
        "calendar:primary": event,
        "tasks:child": {
            "key": "tasks:child",
            "source": "tasks",
            "title": "Pay invoice",
        },
        "gmail:child": {
            "key": "gmail:child",
            "source": "gmail",
            "title": "Invoice email",
        },
    }

    engine._save(state)

    assert engine.acknowledge_notification("calendar:primary") is True

    state = engine._load()

    assert state["pending"] == {}
    assert set(state["history"]) == {
        "calendar:primary",
        "tasks:child",
        "gmail:child",
    }
