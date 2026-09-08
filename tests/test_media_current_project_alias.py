import actions.media as media


def test_production_status_resolves_current_video_project(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:current"] = {
        "brief": "Roma tarixi haqqında YouTube Short hazırla",
        "started_at": 1_000_000,
    }
    monkeypatch.setattr(media, "get_media_job", lambda job_id: "running")
    monkeypatch.setattr(media.time, "time", lambda: 1_000_061)
    monkeypatch.setattr(media, "MEDIA_ROOT", __import__("pathlib").Path("/definitely/missing/media"))

    result = media._media_production_status("current_video_project")

    assert "media:current" in result
    assert "Roma tarixi" in result
    assert "running" in result
    assert "20%" in result
