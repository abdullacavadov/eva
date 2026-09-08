from core.media_video_provider import FAL_MODEL, is_fal_video_enabled


def test_fal_video_provider_is_opt_in(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.setenv("EVA_VIDEO_PROVIDER", "fal_ltx")
    assert is_fal_video_enabled() is False


def test_fal_video_provider_requires_key(monkeypatch):
    monkeypatch.setenv("EVA_VIDEO_PROVIDER", "fal_ltx")
    monkeypatch.setenv("FAL_KEY", "test-key")
    assert is_fal_video_enabled() is True
    assert FAL_MODEL == "fal-ai/ltx-2.3/image-to-video/fast"
