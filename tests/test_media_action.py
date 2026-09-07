import pytest

from actions import media


def test_image_provider_routes_to_image_generation(monkeypatch):
    monkeypatch.setattr(media, "generate_media_image", lambda prompt, filename: f"media/{filename}")

    result = media.play_media("futuristic Baku skyline", provider="image")

    assert result == "Şəkil hazırlandı: media/generated.png"


def test_slideshow_provider_requires_valid_json(monkeypatch):
    monkeypatch.setattr(media, "create_media_slideshow", lambda *args, **kwargs: "media/video.mp4")

    result = media.play_media(
        '{"images":["one.png","two.jpg"],"filename":"test.mp4","seconds_per_image":2}',
        provider="slideshow",
    )

    assert result == "Video hazırlandı: media/video.mp4"


def test_slideshow_provider_rejects_invalid_payload():
    with pytest.raises(ValueError):
        media.play_media("not-json", provider="slideshow")


def test_existing_youtube_playback_path_is_preserved(monkeypatch):
    monkeypatch.setattr(media, "_play_youtube", lambda query: f"youtube:{query}")

    assert media.play_media("EVA music", provider="youtube") == "youtube:EVA music"
