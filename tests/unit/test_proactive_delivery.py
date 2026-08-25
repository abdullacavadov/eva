from core.proactive import ProactiveEngine, ProactiveScheduler


class _Policy:
    def choose(self, pending, history, now):
        return list(pending.values())


def _seed(engine, key="gmail:1"):
    state = engine._load()
    state["pending"][key] = {
        "key": key,
        "source": "gmail",
        "item": {"subject": "Test"},
    }
    engine._save(state)


def test_delivery_failure_keeps_event_pending(tmp_path):
    engine = ProactiveEngine(state_file=tmp_path / "state.json", policy=_Policy())
    _seed(engine)
    scheduler = ProactiveScheduler(engine, lambda event: False)

    assert scheduler.poll_once() == []
    state = engine._load()
    assert "gmail:1" in state["pending"]
    assert "gmail:1" not in state["history"]


def test_successful_delivery_acknowledges_event(tmp_path):
    engine = ProactiveEngine(state_file=tmp_path / "state.json", policy=_Policy())
    _seed(engine)
    scheduler = ProactiveScheduler(engine, lambda event: True)

    delivered = scheduler.poll_once()
    state = engine._load()

    assert len(delivered) == 1
    assert "gmail:1" not in state["pending"]
    assert "gmail:1" in state["history"]


def test_delivery_exception_keeps_event_pending(tmp_path):
    engine = ProactiveEngine(state_file=tmp_path / "state.json", policy=_Policy())
    _seed(engine)

    def fail(_event):
        raise RuntimeError("delivery failed")

    scheduler = ProactiveScheduler(engine, fail)
    assert scheduler.poll_once() == []
    assert "gmail:1" in engine._load()["pending"]
