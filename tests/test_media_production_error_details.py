from actions import media


def test_production_failure_preserves_error_detail(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:failed123"] = {
        "brief": "40 saniyəlik YouTube Short",
        "started_at": 1_000_000,
        "error": "ResourceExhausted: Gemini TTS quota exceeded",
    }

    monkeypatch.setattr(media, "get_media_job", lambda job_id: "failed")
    monkeypatch.setattr(media.time, "time", lambda: 1_000_010)

    result = media._media_production_status("media:failed123")

    assert "Status: failed" in result
    assert "Xəta: ResourceExhausted: Gemini TTS quota exceeded" in result


def test_failed_media_event_stores_real_error(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:failed456"] = {
        "brief": "test video",
        "started_at": 1_000_000,
        "error": "",
    }

    media._media_job_ui_event({
        "job_id": "media:failed456",
        "status": "failed",
        "error": "FFmpegError: filter graph failed",
    })

    assert media._MEDIA_JOBS["media:failed456"]["error"] == "FFmpegError: filter graph failed"
