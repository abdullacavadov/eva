import actions.media as media


def test_production_status_reports_active_job(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:test-status"] = {
        "brief": "Roma tarixi haqqında YouTube Short hazırla",
        "started_at": 1_000_000,
    }
    monkeypatch.setattr(media, "get_media_job", lambda job_id: "running")
    monkeypatch.setattr(media.time, "time", lambda: 1_000_061)
    monkeypatch.setattr(media, "MEDIA_ROOT", __import__("pathlib").Path("/definitely/missing/media"))

    result = media._media_production_status("")

    assert "media:test-status" in result
    assert "Roma tarixi" in result
    assert "Mövzu analiz edilir" in result
    assert "1 dəq 1 san" in result
    assert "20%" in result


def test_production_status_reports_completed_job(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:done"] = {
        "brief": "Roma videosu",
        "started_at": 1_000_000_000,
    }
    monkeypatch.setattr(media, "get_media_job", lambda job_id: "completed")

    result = media._media_production_status("media:done")

    assert "Tamamlandı" in result
    assert "100%" in result
    assert "completed" in result


def test_production_provider_exposes_status(monkeypatch):
    monkeypatch.setattr(media, "_media_production_status", lambda query: f"STATUS:{query}")

    result = media.play_media("media:test-status", provider="production_status")

    assert result == "STATUS:media:test-status"


def test_production_status_resolves_truncated_job_id(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:eea21fed3048"] = {
        "brief": "Piramidaların tikilişi haqqında YouTube Shorts",
        "started_at": 1_000_000,
    }
    monkeypatch.setattr(media, "get_media_job", lambda job_id: "running")
    monkeypatch.setattr(media.time, "time", lambda: 1_000_010)
    monkeypatch.setattr(media, "MEDIA_ROOT", __import__("pathlib").Path("/definitely/missing/media"))

    result = media._media_production_status("eea21fed3048")

    assert "media:eea21fed3048" in result
    assert "Piramidaların tikilişi" in result
    assert "10 san" in result
