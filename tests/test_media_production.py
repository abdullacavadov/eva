from pathlib import Path

import actions.media as media
import core.media_producer as producer


def test_video_creation_language_is_detected():
    assert media._looks_like_video_creation_request("Roma tarixi haqqında YouTube Short hazırla")
    assert media._looks_like_video_creation_request("Roma haqqında böyük video yarat")
    assert not media._looks_like_video_creation_request("YouTube-da Roma videosunu aç")


def test_production_provider_starts_background_job(monkeypatch):
    calls = []
    monkeypatch.setattr(media, "start_media_production", lambda query: calls.append(query) or "media:test123")

    result = media.play_media("Roma tarixi haqqında YouTube Short hazırla", provider="production")

    assert calls == ["Roma tarixi haqqında YouTube Short hazırla"]
    assert result.startswith("Video prodakşn işi başladıldı: media:test123")
    assert "Arxa planda davam edir" in result


def test_auto_provider_routes_video_creation_to_production(monkeypatch):
    calls = []
    monkeypatch.setattr(media, "start_media_production", lambda query: calls.append(query) or "media:auto123")

    result = media.play_media("Roma İmperiyası haqqında video hazırla", provider="auto")

    assert calls == ["Roma İmperiyası haqqında video hazırla"]
    assert "media:auto123" in result


def test_contact_sheet_uses_visual_assets_not_filename_semantics(tmp_path, monkeypatch):
    from PIL import Image

    media_root = tmp_path / "media"
    media_root.mkdir()
    image_path = media_root / "download_184.jpg"
    Image.new("RGB", (640, 360), "black").save(image_path)

    monkeypatch.setattr(producer, "MEDIA_ROOT", media_root)
    sheet = tmp_path / "contact.jpg"
    labels = producer._contact_sheet([image_path], sheet)

    assert sheet.is_file()
    assert labels == ["ASSET 01 = download_184.jpg"]
