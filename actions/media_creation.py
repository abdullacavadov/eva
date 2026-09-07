"""EVA media yaratma əməliyyatlarının təhlükəsiz action qatıdır."""

from __future__ import annotations

from pathlib import Path

from core.media_image import generate_image
from core.media_video import create_slideshow

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_ROOT = (BASE_DIR / "media").resolve()
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}


def _inside_media_root(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        # Model həm "img1.jpg", həm də "media/img1.jpg" qaytara bilər.
        # MEDIA_ROOT artıq "media" qovluğunu göstərdiyi üçün prefiksi
        # bir dəfəlik çıxarırıq və təhlükəsizlik yoxlamasını saxlayırıq.
        parts = candidate.parts
        if parts and parts[0].lower() == "media":
            candidate = Path(*parts[1:]) if len(parts) > 1 else Path(".")
        candidate = MEDIA_ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(MEDIA_ROOT)
    except ValueError as exc:
        raise ValueError("Media faylı yalnız EVA media qovluğunda ola bilər.") from exc
    return candidate


def _resolve_media_image(path: str | Path) -> Path:
    candidate = _inside_media_root(path)
    if candidate.suffix:
        return candidate

    matches = sorted(
        item for item in candidate.parent.glob(f"{candidate.name}.*")
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not matches:
        return candidate
    if len(matches) > 1:
        names = ", ".join(item.name for item in matches)
        raise ValueError(f"Şəkil adı üçün birdən çox uyğun fayl tapıldı: {names}")
    return matches[0]


def _resolve_media_video(path: str | Path) -> Path:
    candidate = _inside_media_root(path)
    if candidate.suffix:
        if candidate.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Dəstəklənməyən video formatı: {candidate.suffix}")
        return candidate

    matches = sorted(
        item for item in candidate.parent.glob(f"{candidate.name}.*")
        if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not matches:
        return candidate
    if len(matches) > 1:
        names = ", ".join(item.name for item in matches)
        raise ValueError(f"Video adı üçün birdən çox uyğun fayl tapıldı: {names}")
    return matches[0]


def list_media_files() -> list[str]:
    """Media qovluğundakı istifadə edilə bilən faylların adlarını qaytarır."""
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return sorted(
        str(item.relative_to(MEDIA_ROOT)).replace("\\", "/")
        for item in MEDIA_ROOT.rglob("*")
        if item.is_file()
        and item.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    )


def generate_media_image(prompt: str, filename: str = "generated.png", *, aspect_ratio: str = "16:9", image_size: str = "1K") -> str:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    destination = _inside_media_root(filename)
    return generate_image(prompt, destination, aspect_ratio=aspect_ratio, image_size=image_size)


def create_media_slideshow(
    image_paths: list[str],
    filename: str = "slideshow.mp4",
    *,
    seconds_per_image: float = 3.0,
    title_text: str = "",
    music_path: str = "",
    music_volume: float = 0.22,
) -> str:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    images = [_resolve_media_image(path) for path in image_paths]
    music = _inside_media_root(music_path) if music_path else None
    destination = _inside_media_root(filename)
    return create_slideshow(
        images,
        destination,
        seconds_per_image=seconds_per_image,
        title_text=title_text,
        music_path=music,
        music_volume=music_volume,
    )


def resolve_media_video(path: str | Path) -> Path:
    """Videonu media qovluğunda ad və ya uzantısı ilə təhlükəsiz şəkildə tapır."""
    return _resolve_media_video(path)
