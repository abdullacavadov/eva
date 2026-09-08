"""EVA üçün ayrıca AI video provider inteqrasiyası."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable

FAL_MODEL = "fal-ai/ltx-2.3/image-to-video/fast"


def is_fal_video_enabled() -> bool:
    """FAL video provider yalnız açıq şəkildə açılıb və açar verilibsə aktivdir."""
    provider = str(os.getenv("EVA_VIDEO_PROVIDER", "ffmpeg")).strip().lower()
    return provider in {"fal", "fal_ltx", "ltx", "ltx-2.3"} and bool(os.getenv("FAL_KEY", "").strip())


def _download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destination)
    return destination


def generate_video_clip(
    image_path: str | Path,
    prompt: str,
    destination: str | Path,
    *,
    duration: float = 6.0,
    portrait: bool = False,
    on_update: Callable[[str], None] | None = None,
) -> Path:
    """Bir lokal şəkildən LTX-2.3 ilə AI video klipi yaradır."""
    if not os.getenv("FAL_KEY", "").strip():
        raise RuntimeError("AI video provider üçün FAL_KEY konfiqurasiya edilməyib.")
    try:
        import fal_client
    except ImportError as exc:
        raise RuntimeError("fal-client quraşdırılmayıb. `pip install fal-client` icra et.") from exc

    if on_update:
        on_update("Şəkil fal.ai storage-a yüklənir")
    image_url = fal_client.upload_file(str(image_path))
    seconds = max(6, min(20, round(float(duration))))
    if on_update:
        on_update(f"LTX-2.3 video səhnəsi yaradılır — {seconds} san")
    result = fal_client.subscribe(
        FAL_MODEL,
        arguments={
            "image_url": image_url,
            "prompt": str(prompt or "").strip() or "Natural cinematic camera movement.",
            "duration": seconds,
            "resolution": "1080p",
            "aspect_ratio": "9:16" if portrait else "16:9",
            "fps": 25,
            "generate_audio": False,
        },
        with_logs=True,
    )
    video = result.get("video") if isinstance(result, dict) else None
    url = video.get("url") if isinstance(video, dict) else None
    if not url:
        raise RuntimeError("fal.ai LTX-2.3 video çıxışı qaytarmadı.")
    return _download(str(url), Path(destination))


def render_video_scenes(
    scenes: list[dict],
    output: Path,
    *,
    width: int,
    height: int,
    narration: Path | None,
    music: Path | None,
    on_update: Callable[[str, int], None] | None = None,
) -> str:
    """AI kliplərini yaradıb FFmpeg ilə narration/music ilə birləşdirir."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg tapılmadı. FFmpeg-i quraşdırıb PATH-a əlavə et.")
    if not scenes:
        raise ValueError("Video üçün səhnə planı boşdur.")

    portrait = height > width
    with tempfile.TemporaryDirectory(prefix="eva_ltx_") as temp_dir:
        work = Path(temp_dir)
        clips: list[Path] = []
        for index, scene in enumerate(scenes):
            clip = work / f"ai_scene_{index:03d}.mp4"
            generate_video_clip(
                scene["path"],
                str(scene.get("visual_prompt") or "cinematic natural movement"),
                clip,
                duration=float(scene.get("duration", 6.0) or 6.0),
                portrait=portrait,
            )
            clips.append(clip)
            if on_update:
                on_update(f"AI video səhnəsi {index + 1}/{len(scenes)} hazırdır", round((index + 1) / len(scenes) * 75))

        inputs: list[str] = []
        filters: list[str] = []
        durations: list[float] = []
        for clip in clips:
            inputs += ["-i", str(clip)]
            durations.append(6.0)
        current = "[0:v]"
        elapsed = durations[0]
        for index in range(1, len(clips)):
            trans = 0.5
            offset = max(0.0, elapsed - trans)
            out = f"v{index}"
            filters.append(f"{current}[{index}:v]xfade=transition=fade:duration={trans}:offset={offset}[{out}]")
            current = f"[{out}]"
            elapsed += durations[index] - trans
        silent = work / "silent.mp4"
        subprocess.run(
            [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", current, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent)],
            capture_output=True,
            text=True,
            check=True,
        )

        audio_inputs: list[str] = []
        if narration and narration.is_file():
            audio_inputs += ["-i", str(narration)]
        if music and music.is_file():
            audio_inputs += ["-stream_loop", "-1", "-i", str(music)]
        final = [ffmpeg, "-y", "-i", str(silent), *audio_inputs]
        if narration and narration.is_file() and music and music.is_file():
            final += ["-filter_complex", "[1:a]volume=1.0[n];[2:a]volume=0.18[m];[n][m]amix=inputs=2:duration=first:dropout_transition=2[aout]", "-map", "0:v:0", "-map", "[aout]"]
        elif audio_inputs:
            final += ["-map", "0:v:0", "-map", "1:a:0"]
        else:
            final += ["-map", "0:v:0", "-an"]
        final += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output)]
        subprocess.run(final, capture_output=True, text=True, check=True)
    return str(output)
