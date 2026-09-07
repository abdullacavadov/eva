from pathlib import Path

import pytest
from PIL import Image

from actions.media_creation import _inside_media_root
from core.media_video import _prepare_frame, _resolve_image


def test_media_paths_are_confined_to_media_root():
    assert _inside_media_root("renders/test.png").name == "test.png"
    with pytest.raises(ValueError):
        _inside_media_root("../outside.png")


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
