from pathlib import Path

from actions import media


def test_media_start_notification_uses_start_sfx(monkeypatch):
    played: list[str] = []

    monkeypatch.setattr(media.os, "name", "nt")
    monkeypatch.setattr(media.os, "startfile", lambda path: played.append(path), raising=False)

    media._play_background_notification_sfx()

    assert played == [str(Path(media.__file__).resolve().parent.parent / "SFX" / "Start.mp3")]


def test_media_start_notification_is_noop_without_sfx(monkeypatch, tmp_path):
    played: list[str] = []

    monkeypatch.setattr(media.os, "name", "nt")
    monkeypatch.setattr(media.os, "startfile", lambda path: played.append(path), raising=False)
    monkeypatch.setattr(media.Path, "__new__", lambda cls, *args, **kwargs: tmp_path / "missing")

    media._play_background_notification_sfx()

    assert played == []
