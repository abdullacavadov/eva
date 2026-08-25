from core.proactive import ProactiveEngine
from core.proactive_digest_scheduler import ProactiveDigestScheduler


def _seed(engine):
    state = engine._load()
    state["pending"] = {
        "gmail:1": {
            "key": "gmail:1",
            "source": "gmail",
            "item": {"subject": "A"},
        },
        "whatsapp:2": {
            "key": "whatsapp:2",
            "source": "whatsapp",
            "item": {"title": "B"},
        },
    }
    engine._save(state)


def test_digest_delivery_failure_keeps_children_pending(tmp_path):
    engine = ProactiveEngine(tmp_path / "state.json")
    _seed(engine)
    scheduler = ProactiveDigestScheduler(engine, lambda event: False)

    digest = scheduler.build()
    assert digest["count"] == 2
    assert scheduler.acknowledge(digest) is False
    assert set(engine._load()["pending"]) == {"gmail:1", "whatsapp:2"}


def test_successful_digest_acknowledges_all_children(tmp_path):
    engine = ProactiveEngine(tmp_path / "state.json")
    _seed(engine)
    scheduler = ProactiveDigestScheduler(engine, lambda event: True)

    digest = scheduler.build()
    assert scheduler.acknowledge(digest) is True

    state = engine._load()
    assert state["pending"] == {}
    assert set(state["history"]) == {"gmail:1", "whatsapp:2"}


def test_empty_pending_has_no_digest(tmp_path):
    engine = ProactiveEngine(tmp_path / "state.json")
    scheduler = ProactiveDigestScheduler(engine, lambda event: True)

    assert scheduler.build() is None
