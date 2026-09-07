from pathlib import Path

import pytest
from PIL import Image

from actions.media_creation import MEDIA_ROOT, _inside_media_root, _resolve_media_image
from core.media_video import _prepare_frame, _resolve_image


def test_media_paths_are_confined_to_media_root():
    assert _inside_media_root("renders/test.png").name == "test.png"
    assert _inside_media_root("media/renders/test.png") == MEDIA_ROOT / "renders" / "test.png"
    assert _inside_media_root("MEDIA/renders/test.png") == MEDIA_ROOT / "renders" / "test.png"
    with pytest.raises(ValueError):
        _inside_media_root("../outside.png")


def test_resolve_media_image_finds_supported_extension(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    image = tmp_path / "img2.jpeg"
    image.touch()

    assert _resolve_media_image("img2") == image
    assert _resolve_media_image("media/img2") == image


def test_resolve_media_image_rejects_ambiguous_extension(tmp_path, monkeypatch):
    monkeypatch.setattr("actions.media_creation.MEDIA_ROOT", tmp_path)
    (tmp_path / "img2.jpg").touch()
    (tmp_path / "img2.png").touch()

    with pytest.raises(ValueError, match="birdən çox uyğun fayl"):
        _resolve_media_image("img2")


def test_prepare_frame_writes_standardized_png(tmp_path):
    source = tmp_path / "source.jpg"
    target = tmp_path / "frame.png"
    Image.new("RGB", (640, 480), (20, 30, 40)).save(source)

    _prepare_frame(source, target, width=1280, height=720, text="EVA")

    with Image.open(target) as rendered:
        assert rendered.size == (1280, 720)
        assert rendered.mode == "RGB"


def test_resolve_image_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        _resolve_image(tmp_path / "missing.png")
