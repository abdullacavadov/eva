from pathlib import Path

import pytest

import actions.media as media
from actions.media_creation import list_media_files, resolve_media_video


def test_list_media_files_returns_supported_media(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    (tmp_path / "img1.jpg").touch()
    (tmp_path / "img2.png").touch()
    (tmp_path / "video.mp4").touch()
    (tmp_path / "song.mp3").touch()
    (tmp_path / "notes.txt").touch()

    assert list_media_files() == ["img1.jpg", "img2.png", "song.mp3", "video.mp4"]


def test_resolve_media_video_finds_extensionless_name(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    video = tmp_path / "slideshow.mp4"
    video.touch()

    assert resolve_media_video("slideshow") == video
    assert resolve_media_video("media/slideshow") == video


def test_resolve_media_video_rejects_ambiguous_name(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    (tmp_path / "slideshow.mp4").touch()
    (tmp_path / "slideshow.webm").touch()

    with pytest.raises(ValueError, match="birdən çox uyğun video"):
        resolve_media_video("slideshow")


def test_open_video_uses_default_windows_handler(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(media, "MEDIA_ROOT", tmp_path)
    video = tmp_path / "slideshow.mp4"
    video.touch()
    monkeypatch.setattr(media.os, "name", "nt")
    opened = []
    monkeypatch.setattr(media.os, "startfile", lambda path: opened.append(path), raising=False)

    result = media._open_video("slideshow")

    assert result == f"Video açıldı: {video}"
    assert opened == [str(video)]


def test_open_media_folder_uses_windows_explorer(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(media, "MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(media.os, "name", "nt")
    opened = []
    monkeypatch.setattr(media.os, "startfile", lambda path: opened.append(path), raising=False)

    result = media._open_media_folder()

    assert result == str(tmp_path)
    assert opened == [str(tmp_path)]
