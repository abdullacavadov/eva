from pathlib import Path
from types import SimpleNamespace

from actions import media


def test_media_start_notification_uses_start_sfx(monkeypatch):
    played: list[str] = []

    monkeypatch.setattr(
        media,
        "os",
        SimpleNamespace(
            name="nt",
            startfile=lambda path: played.append(path),
        ),
    )

    media._play_background_notification_sfx()

    assert played == [str(Path(media.__file__).resolve().parent.parent / "SFX" / "Done.mp3")]
