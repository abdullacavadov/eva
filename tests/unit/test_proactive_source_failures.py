from core.proactive import ProactiveEngine


class _Policy:
    def choose(self, pending, history, now):
        return []


def test_gmail_failure_does_not_replace_snapshot(monkeypatch, tmp_path):
    engine = ProactiveEngine(state_file=tmp_path / "state.json", policy=_Policy())
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [{"id": "1", "subject": "A"}]})
    engine.poll()
    first = engine._load()["snapshots"]["gmail"]

    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": None})
    engine.poll()
    second = engine._load()["snapshots"]["gmail"]

    assert second == first


def test_failed_source_is_not_treated_as_empty(monkeypatch, tmp_path):
    engine = ProactiveEngine(state_file=tmp_path / "state.json", policy=_Policy())
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [{"id": "1", "subject": "A"}]})
    engine.poll()

    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": None})
    engine.poll()
    state = engine._load()

    assert state["snapshots"]["gmail"]["items"]
    assert state["pending"] == {}


def test_source_recovery_does_not_create_false_new_event(monkeypatch, tmp_path):
    engine = ProactiveEngine(state_file=tmp_path / "state.json", policy=_Policy())
    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [{"id": "1", "subject": "A"}]})
    engine.poll()

    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": None})
    engine.poll()

    monkeypatch.setattr(engine, "_collect", lambda: {"gmail": [{"id": "1", "subject": "A"}]})
    engine.poll()

    assert engine._load()["pending"] == {}
