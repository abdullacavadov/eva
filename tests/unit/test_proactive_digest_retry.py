from __future__ import annotations

from datetime import datetime, timezone

from core.proactive import ProactiveEngine, NotificationPolicy


def _now(hour: int = 8, minute: int = 0) -> datetime:
    return datetime(2026, 8, 25, hour, minute, tzinfo=timezone.utc)


def _pending(key: str, subject: str) -> dict:
    return {"key": key, "source": "gmail", "item": {"subject": subject}, "changed": True}


def test_quiet_digest_retries_after_failed_delivery(tmp_path, monkeypatch):
    engine = ProactiveEngine(tmp_path / "proactive-state.json", NotificationPolicy(quiet_start="23:00", quiet_end="07:00"))
    pending = {"gmail:1": _pending("gmail:1", "First"), "gmail:2": _pending("gmail:2", "Second")}
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [], "calendar": [], "tasks": [], "memory": {}})
    state = engine._load()
    state["pending"] = pending
    state["last_poll"] = _now(2).isoformat()
    engine._save(state)

    first = engine.poll(_now(8))
    assert len(first) == 1
    assert first[0]["key"].startswith("digest:")

    retry = engine.poll(_now(8, 2))
    assert len(retry) == 1
    assert retry[0]["key"] == first[0]["key"]


def test_digest_ack_only_removes_offered_children(tmp_path):
    engine = ProactiveEngine(tmp_path / "proactive-state.json")
    offered = {"gmail:1": _pending("gmail:1", "First"), "gmail:2": _pending("gmail:2", "Second")}
    state = engine._load()
    state["pending"] = {**offered, "gmail:new": _pending("gmail:new", "Arrived later")}
    state["quiet_digest_sent"] = "digest:test"
    state["quiet_digest_keys"] = list(offered)
    state["quiet_digest_offered_at"] = _now(8).isoformat()
    engine._save(state)

    assert engine.acknowledge_digest("digest:test", _now(8, 1)) is True

    state = engine._load()
    assert set(state["pending"]) == {"gmail:new"}
    assert set(state["history"]) == set(offered)
    assert state["quiet_digest_sent"] is None
    assert state["quiet_digest_keys"] == []


def test_digest_ack_is_not_available_for_unknown_key(tmp_path):
    engine = ProactiveEngine(tmp_path / "proactive-state.json")
    state = engine._load()
    state["pending"] = {"gmail:1": _pending("gmail:1", "First")}
    state["quiet_digest_sent"] = "digest:known"
    state["quiet_digest_keys"] = ["gmail:1"]
    engine._save(state)

    assert engine.acknowledge_digest("digest:unknown", _now()) is False
    state = engine._load()
    assert "gmail:1" in state["pending"]
