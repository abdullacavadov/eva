from __future__ import annotations

from datetime import datetime, timezone

from core.proactive import NotificationPolicy, ProactiveEngine, ProactiveScheduler


def _now(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 25, hour, minute, tzinfo=timezone.utc)


def _sources(items):
    return {
        "gmail": items,
        "whatsapp": [],
        "calendar": [],
        "tasks": [],
        "memory": {},
    }


def test_quiet_hours_release_multiple_events_as_digest(tmp_path, monkeypatch):
    engine = ProactiveEngine(
        tmp_path / "state.json",
        NotificationPolicy(rate_limit=3, quiet_start="23:00", quiet_end="07:00"),
    )
    values = [
        [{"id": "1", "subject": "Existing"}],
        [
            {"id": "1", "subject": "Existing"},
            {"id": "2", "subject": "Night 1"},
            {"id": "3", "subject": "Night 2"},
        ],
    ]
    monkeypatch.setattr(engine, "_collect", lambda: _sources(values.pop(0)))
    assert engine.poll(_now(22)) == []
    assert engine.poll(_now(6)) == []

    values.append([])
    monkeypatch.setattr(engine, "_collect", lambda: _sources(values.pop(0)))
    digest = engine.poll(_now(8))

    assert len(digest) == 1
    assert digest[0]["source"] == "digest"
    assert digest[0]["count"] == 2
    assert digest[0]["counts"] == {"gmail": 2}


def test_failed_digest_delivery_remains_pending(tmp_path):
    class FakeEngine:
        def __init__(self):
            self.acked = False

        def poll(self):
            return [{"key": "digest:test", "source": "digest", "count": 2}]

        def acknowledge_digest(self, key):
            self.acked = True
            return True

    received = []
    scheduler = ProactiveScheduler(FakeEngine(), lambda event: False, interval=10)
    assert scheduler.poll_once() == []
    assert received == []


def test_successful_digest_delivery_uses_digest_ack():
    class FakeEngine:
        def __init__(self):
            self.ack_keys = []

        def poll(self):
            return [{"key": "digest:test", "source": "digest", "count": 2}]

        def acknowledge_digest(self, key):
            self.ack_keys.append(key)
            return True

    engine = FakeEngine()
    scheduler = ProactiveScheduler(engine, lambda event: True, interval=10)
    delivered = scheduler.poll_once()

    assert [event["key"] for event in delivered] == ["digest:test"]
    assert engine.ack_keys == ["digest:test"]
