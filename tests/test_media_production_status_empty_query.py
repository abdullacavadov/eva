from actions import media


def test_production_status_accepts_empty_query(monkeypatch):
    media._MEDIA_JOBS.clear()
    media._MEDIA_JOBS["media:test123"] = {
        "brief": "Piramidaların tikilişi haqqında YouTube Short",
        "started_at": 1_000_000,
    }

    monkeypatch.setattr(media, "get_media_job", lambda job_id: "running")
    monkeypatch.setattr(media.time, "time", lambda: 1_000_010)
    monkeypatch.setattr(media, "_production_stage", lambda job_id: ("Mövzu analiz edilir və vizuallar seçilir", 20))

    result = media.play_media("", provider="production_status")

    assert "media:test123" in result
    assert "Piramidaların tikilişi" in result
    assert "Status: running" in result
    assert "10 san" in result
