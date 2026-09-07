"""EVA üçün şəkil -> video kompozisiya mühərriki.

FFmpeg yalnız deterministik render mərhələsində istifadə olunur. Modelin
verdiyi mətn birbaşa shell sətrinə qoşulmur; bütün arqumentlər subprocess-a
ayrı elementlər kimi ötürülür.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FONT = BASE_DIR / "Fonts" / "Grift-Regular.ttf"


def _require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg tapılmadı. FFmpeg-i quraşdırıb PATH-a əlavə et.")
    return ffmpeg


def _resolve_image(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Şəkil tapılmadı: {resolved}")
    if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"Dəstəklənməyən şəkil formatı: {resolved.suffix}")
    return resolved


def _prepare_frame(source: Path, destination: Path, *, width: int, height: int, text: str = "", font_path: Path | None = None) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), (0, 0, 0))
        x = (width - image.width) // 2
        y = (height - image.height) // 2
        canvas.paste(image, (x, y))

        if text.strip():
            draw = ImageDraw.Draw(canvas, "RGBA")
            font_file = font_path if font_path and font_path.is_file() else DEFAULT_FONT
            try:
                font = ImageFont.truetype(str(font_file), 54)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.multiline_textbbox((0, 0), text.strip(), font=font, spacing=8, align="center")
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            padding = 28
            box = (width // 2 - tw // 2 - padding, height - th - 70 - padding, width // 2 + tw // 2 + padding, height - 70 + padding)
            draw.rounded_rectangle(box, radius=18, fill=(0, 0, 0, 175))
            draw.multiline_text((width // 2, height - 70), text.strip(), font=font, fill=(255, 255, 255, 255), anchor="ms", spacing=8, align="center")

        canvas.save(destination, format="PNG")


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "FFmpeg uğursuz oldu.").strip()
        raise RuntimeError(detail[-1000:])


def create_slideshow(
    images: list[str | Path],
    output_path: str | Path,
    *,
    seconds_per_image: float = 3.0,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    title_text: str = "",
    music_path: str | Path | None = None,
    music_volume: float = 0.22,
) -> str:
    """Şəkillərdən MP4 slideshow yaradır və istəyə görə musiqi əlavə edir."""
    if not images:
        raise ValueError("Video üçün ən azı bir şəkil lazımdır.")
    if seconds_per_image <= 0:
        raise ValueError("Şəkil müddəti 0-dan böyük olmalıdır.")
    if fps <= 0:
        raise ValueError("FPS 0-dan böyük olmalıdır.")
    if not 0 < music_volume <= 1:
        raise ValueError("Musiqi səsi 0-dan böyük və 1-dən kiçik/bərabər olmalıdır.")

    ffmpeg = _require_ffmpeg()
    source_images = [_resolve_image(item) for item in images]
    destination = Path(output_path).expanduser()
    if destination.suffix.lower() != ".mp4":
        raise ValueError("Video çıxışı MP4 olmalıdır.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = destination.resolve()

    music = None
    if music_path:
        music = Path(music_path).expanduser().resolve()
        if not music.is_file():
            raise FileNotFoundError(f"Musiqi faylı tapılmadı: {music}")

    with tempfile.TemporaryDirectory(prefix="eva_media_") as temp_dir:
        work = Path(temp_dir)
        frame_paths: list[Path] = []
        for index, source in enumerate(source_images):
            frame = work / f"frame_{index:04d}.png"
            _prepare_frame(source, frame, width=width, height=height, text=title_text)
            frame_paths.append(frame)

        concat_file = work / "concat.txt"
        duration = f"{seconds_per_image:.6f}"
        lines: list[str] = []
        for frame in frame_paths:
            safe = str(frame).replace("'", "'\\''")
            lines.append(f"file '{safe}'")
            lines.append(f"duration {duration}")
        # concat demuxer applies the final duration only when the last frame
        # is repeated.
        safe_last = str(frame_paths[-1]).replace("'", "'\\''")
        lines.append(f"file '{safe_last}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        silent_video = work / "video.mp4"
        _run([
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent_video),
        ])

        if music is None:
            shutil.copyfile(silent_video, destination)
        else:
            _run([
                ffmpeg, "-y", "-i", str(silent_video), "-stream_loop", "-1", "-i", str(music),
                "-filter:a", f"volume={music_volume:.3f}", "-shortest",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(destination),
            ])

    return str(destination)
