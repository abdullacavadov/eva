from core import media_observability


def test_media_observability_stage_order(monkeypatch):
    events = []

    class Bridge:
        def emit(self, event_type, **payload):
            events.append((event_type, payload))

    media_observability._INSTALLED = False
    media_observability._CURRENT_JOB = ""

    import core.media_producer as producer
    original_notify = producer._notify
    monkeypatch.setattr(producer, "_notify", lambda event: events.append(("notify", event)))
    monkeypatch.setattr(producer, "_plan", lambda *args: {
        "narration": "Test narrasiya",
        "scenes": [{"asset": "GENERATE", "visual_prompt": "test", "duration": 6}],
    })

    media_observability.install(Bridge())
    producer._notify({"job_id": "media:test", "status": "started", "brief": "test"})
    result = producer._plan("test", None, [], [])

    assert result["narration"] == "Test narrasiya"
    media_events = [payload["data"] for kind, payload in events if kind == "media.production"]
    stages = [item.get("stage") for item in media_events if item.get("stage")]
    assert "queued" in stages
    assert "transcribing" in stages
    assert "planning_scenes" in stages
    assert "transcript_ready" in stages
    assert "scenes_ready" in stages

    media_observability._INSTALLED = False
    media_observability._CURRENT_JOB = ""
    producer._notify = original_notify
