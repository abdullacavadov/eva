import threading
import time

from core.proactive import ProactiveScheduler


class _Engine:
    def __init__(self):
        self.calls = 0

    def poll(self):
        self.calls += 1
        return []


def test_scheduler_start_is_idempotent():
    engine = _Engine()
    scheduler = ProactiveScheduler(engine, lambda event: True, interval=10)
    scheduler.start()
    first = scheduler._thread
    scheduler.start()
    second = scheduler._thread
    scheduler.stop()
    assert first is second


def test_scheduler_stop_signals_worker():
    engine = _Engine()
    scheduler = ProactiveScheduler(engine, lambda event: True, interval=10)
    scheduler.start()
    scheduler.stop()
    scheduler._thread.join(timeout=1)
    assert not scheduler._thread.is_alive()


def test_scheduler_worker_survives_poll_exception():
    class FailingEngine:
        def __init__(self):
            self.calls = 0

        def poll(self):
            self.calls += 1
            raise RuntimeError("temporary source failure")

    engine = FailingEngine()
    scheduler = ProactiveScheduler(engine, lambda event: True, interval=10)
    scheduler.start()
    deadline = time.time() + 1
    while engine.calls == 0 and time.time() < deadline:
        time.sleep(0.01)
    assert engine.calls > 0
    assert scheduler._thread.is_alive()
    scheduler.stop()
    scheduler._thread.join(timeout=1)
    assert not scheduler._thread.is_alive()
