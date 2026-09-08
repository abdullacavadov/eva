from core import media_observability


def test_planner_retries_transient_503(monkeypatch):
    calls = []
    sleeps = []

    def flaky_plan(*args):
        calls.append(len(calls) + 1)
        if len(calls) < 3:
            raise RuntimeError("503 UNAVAILABLE")
        return {"title": "Test", "scenes": []}

    monkeypatch.setattr(media_observability.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = media_observability._plan_with_retry(flaky_plan, "test", None, [], [])

    assert result["title"] == "Test"
    assert calls == [1, 2, 3]
    assert sleeps == [1, 2]


def test_planner_does_not_retry_non_transient_error(monkeypatch):
    calls = []
    sleeps = []

    def failing_plan(*args):
        calls.append(1)
        raise RuntimeError("Invalid planner schema")

    monkeypatch.setattr(media_observability.time, "sleep", lambda seconds: sleeps.append(seconds))

    try:
        media_observability._plan_with_retry(failing_plan, "test", None, [], [])
    except RuntimeError as exc:
        assert str(exc) == "Invalid planner schema"
    else:
        raise AssertionError("Non-transient planner error must be raised immediately")

    assert len(calls) == 1
    assert sleeps == []
