from pathlib import Path

from actions import media


def test_media_start_notification_uses_start_sfx(monkeypatch):
    played: list[str] = []

    monkeypatch.setattr(media.os, "name", "nt")
    monkeypatch.setattr(media.os, "startfile", lambda path: played.append(path), raising=False)

    media._play_background_notification_sfx()

    assert played == [str(Path(media.__file__).resolve().parent.parent / "SFX" / "Start.mp3")]
