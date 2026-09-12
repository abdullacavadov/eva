"""EVA-nın avtonom YouTube video prodakşn pipeline-ı."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
import wave
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

from core.config import get_api_key
from core.media_image import generate_image

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_ROOT = (BASE_DIR / "media").resolve()
PLANNER_MODEL = "gemini-3.8-flash"
TTS_MODEL = "gemini-3.1-flash-tts-preview"
MUSIC_MODEL = "lyria-3.5"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
FPS = 30

_JOB_LOCK = threading.Lock()
_JOBS: dict[str, str] = {}
_NOTIFY: Callable[[dict], None] | None = None


def set_job_notifier(callback: Callable[[dict], None] | None) -> None:
    global _NOTIFY
    _NOTIFY = callback


def _notify(event: dict) -> None:
    callback = _NOTIFY
    if callback is not None:
        try:
            callback(dict(event))
        except Exception:
            pass


def _safe_name(value: str, fallback: str = "eva_video") -> str:
    clean = re.sub(r"[^\w\-. ]+", "", str(value or "")).strip()
    clean = re.sub(r"\s+", "_", clean)
    return clean[:80] or fallback


def _inside_media(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    parts = candidate.parts
    if parts and parts[0].lower() == "media":
        candidate = Path(*parts[1:]) if len(parts) > 1 else Path(".")
    if not candidate.is_absolute():
        candidate = MEDIA_ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(MEDIA_ROOT)
    except ValueError as exc:
        raise ValueError("Media faylı yalnız EVA media qovluğunda ola bilər.") from exc
    return candidate


def _media_images() -> list[Path]:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return sorted(
        item for item in MEDIA_ROOT.rglob("*")
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def _media_audio() -> list[Path]:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return sorted(
        item for item in MEDIA_ROOT.rglob("*")
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS
    )


def _contact_sheet(images: list[Path], destination: Path) -> list[str]:
    images = images[:24]
    if not images:
        return []
    thumb_w, thumb_h = 300, 190
    cols = 4
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "#101010")
    draw = ImageDraw.Draw(sheet)
    labels: list[str] = []
    for index, path in enumerate(images, 1):
        x = ((index - 1) % cols) * thumb_w
        y = ((index - 1) // cols) * thumb_h
        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((thumb_w - 12, thumb_h - 42), Image.Resampling.LANCZOS)
                px = x + (thumb_w - image.width) // 2
                py = y + 6
                sheet.paste(image, (px, py))
        except Exception:
            pass
        draw.rectangle((x, y + thumb_h - 34, x + thumb_w, y + thumb_h), fill="#000000")
        draw.text((x + 8, y + thumb_h - 28), f"ASSET {index:02d}", fill="white")
        labels.append(f"ASSET {index:02d} = {path.relative_to(MEDIA_ROOT).as_posix()}")
    sheet.save(destination, format="JPEG", quality=82, optimize=True)
    return labels


def _planner_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "orientation": {"type": "string", "enum": ["landscape", "portrait"]},
            "duration_seconds": {"type": "number"},
            "narration": {"type": "string"},
            "music_prompt": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "asset": {"type": "string"},
                        "visual_prompt": {"type": "string"},
                        "onscreen_text": {"type": "string"},
                        "duration": {"type": "number"},
                        "transition": {"type": "string"},
                    },
                    "required": ["asset", "visual_prompt", "onscreen_text", "duration", "transition"],
                },
            },
        },
        "required": ["title", "orientation", "duration_seconds", "narration", "music_prompt", "scenes"],
    }


def _plan(brief: str, contact_sheet: Path | None, asset_labels: list[str], audio_labels: list[str]) -> dict:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Gemini API açarı konfiqurasiya edilməyib.")
    client = genai.Client(api_key=api_key)
    asset_text = "\n".join(asset_labels) if asset_labels else "Heç bir lokal şəkil yoxdur."
    audio_text = "\n".join(f"MUSİQİ: {p}" for p in audio_labels) if audio_labels else "Lokal musiqi yoxdur; lazım olsa Gemini ilə yarat."
    prompt = f"""Sən EVA üçün peşəkar YouTube video prodüserisən. İstifadəçinin tələbi:
{brief}

Videonu özün planla. Mövzunu faktiki və məntiqli ardıcıllıqla qur. Short üçün portret, böyük video üçün landşaft seç. Səhnələri 2-6 saniyəlik dinamik bloklara böl; uzun videoda daha çox səhnə istifadə et.

LOKAL ŞƏKİL AKTİVLƏRİ aşağıdadır. Şəkilləri fayl adından deyil, kontakt vərəqindəki vizual məzmunundan qiymətləndir. Səhnə üçün uyğun vizual varsa onun ASSET nömrəsini seç. Uyğun vizual yoxdursa asset='GENERATE' yaz və visual_prompt ilə Gemini-yə fotorealistik/tarixi uyğun şəkil təsviri ver.
{asset_text}

LOKAL AUDIO:
{audio_text}

Keçidlər üçün yalnız bunlardan istifadə et: fade, fadeblack, dissolve, wipeleft, wiperight, slideleft, slideright. Eyni keçidi bütün səhnələrdə məcburi təkrarlama; mövzuya uyğun seç.

Narration Azərbaycan dilində olsun, təbii YouTube aparıcısı üslubunda, uydurma faktlardan qaç. Onscreen text qısa və oxunaqlı olsun.
"""
    contents: list[object] = [prompt]
    if contact_sheet is not None:
        with contact_sheet.open("rb") as fh:
            contents.append(types.Part.from_bytes(data=fh.read(), mime_type="image/jpeg"))
    response = client.models.generate_content(
        model=PLANNER_MODEL,
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": _planner_schema(),
        },
    )
    if not response.text:
        raise RuntimeError("Gemini video planı qaytarmadı.")
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini video planını JSON kimi oxumaq mümkün olmadı.") from exc


def _generate_narration(text: str, destination: Path) -> Path:
    if not text.strip():
        return destination
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Gemini API açarı konfiqurasiya edilməyib.")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=text.strip(),
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                )
            ),
        ),
    )
    data = None
    for part in getattr(response, "parts", []) or []:
        inline = getattr(part, "inline_data", None)
        if inline is not None:
            data = inline.data
            break
    if not data:
        raise RuntimeError("Gemini TTS audio çıxışı qaytarmadı.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(data)
    return destination


def _generate_music(prompt: str, destination: Path) -> Path | None:
    if not prompt.strip():
        return None
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MUSIC_MODEL,
            contents=prompt.strip(),
            config=types.GenerateContentConfig(response_modalities=["AUDIO", "TEXT"]),
        )
        for part in getattr(response, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and inline.data:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(inline.data)
                return destination
    except Exception:
        return None
    return None


def _duration_seconds(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return max(0.0, float(completed.stdout.strip()))
    except (TypeError, ValueError):
        return 0.0


def _scene_frame(source: Path, destination: Path, text: str, width: int, height: int) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        src_ratio = image.width / max(1, image.height)
        target_ratio = width / height
        if src_ratio > target_ratio:
            crop_w = int(image.height * target_ratio)
            left = max(0, (image.width - crop_w) // 2)
            image = image.crop((left, 0, left + crop_w, image.height))
        else:
            crop_h = int(image.width / target_ratio)
            top = max(0, (image.height - crop_h) // 2)
            image = image.crop((0, top, image.width, top + crop_h))
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(image, "RGBA")
        if text.strip():
            font = None
            for candidate in (BASE_DIR / "Fonts" / "Grift-Regular.ttf",):
                if candidate.is_file():
                    try:
                        font = ImageFont.truetype(str(candidate), max(42, width // 34))
                        break
                    except Exception:
                        pass
            if font is None:
                font = ImageFont.load_default()
            bbox = draw.multiline_textbbox((0, 0), text.strip(), font=font, spacing=8, align="center")
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pad_x, pad_y = 36, 24
            x0 = (width - tw) // 2 - pad_x
            y0 = height - th - 110 - pad_y
            x1 = (width + tw) // 2 + pad_x
            y1 = height - 110 + pad_y
            draw.rounded_rectangle((x0, y0, x1, y1), radius=20, fill=(0, 0, 0, 180))
            draw.multiline_text((width // 2, height - 110), text.strip(), font=font, fill="white", anchor="ms", spacing=8, align="center")
        image.save(destination, format="PNG")


def _render_scenes(scenes: list[dict], output: Path, *, width: int, height: int, narration: Path | None, music: Path | None) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg tapılmadı. FFmpeg-i quraşdırıb PATH-a əlavə et.")
    if not scenes:
        raise ValueError("Video üçün səhnə planı boşdur.")

    with tempfile.TemporaryDirectory(prefix="eva_production_") as temp_dir:
        work = Path(temp_dir)
        clips: list[Path] = []
        durations: list[float] = []
        for index, scene in enumerate(scenes):
            duration = max(1.5, float(scene.get("duration", 3.0) or 3.0))
            frame = work / f"scene_{index:03d}.png"
            clip = work / f"clip_{index:03d}.mp4"
            _scene_frame(Path(scene["path"]), frame, str(scene.get("onscreen_text", "")), width, height)
            subprocess.run(
                [ffmpeg, "-y", "-loop", "1", "-i", str(frame), "-t", f"{duration:.3f}", "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)],
                capture_output=True, text=True, check=True,
            )
            clips.append(clip)
            durations.append(duration)

        if len(clips) == 1:
            silent = clips[0]
            shutil.copyfile(silent, output)
        else:
            inputs: list[str] = []
            for clip in clips:
                inputs += ["-i", str(clip)]
            filters: list[str] = []
            current = "[0:v]"
            elapsed = durations[0]
            for index in range(1, len(clips)):
                transition = str(scenes[index].get("transition", "fade")).lower()
                transition = {"dissolve": "fade", "fade-to-black": "fadeblack"}.get(transition, transition)
                if transition not in {"fade", "fadeblack", "wipeleft", "wiperight", "slideleft", "slideright", "circleopen", "circleclose"}:
                    transition = "fade"
                trans = min(0.9, max(0.35, durations[index] * 0.25), durations[index - 1] * 0.35)
                offset = max(0.0, elapsed - trans)
                out = f"v{index}"
                filters.append(f"{current}[{index}:v]xfade=transition={transition}:duration={trans:.3f}:offset={offset:.3f}[{out}]")
                current = f"[{out}]"
                elapsed += durations[index] - trans
            silent = work / "silent.mp4"
            _run_ffmpeg = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", current, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent)]
            subprocess.run(_run_ffmpeg, capture_output=True, text=True, check=True)

        audio_inputs: list[str] = []
        filters_audio: list[str] = []
        maps: list[str] = ["-map", "0:v:0"]
        audio_index = 1
        if narration is not None and narration.is_file():
            audio_inputs += ["-i", str(narration)]
            maps += ["-map", f"{audio_index}:a:0"]
            audio_index += 1
        if music is not None and music.is_file():
            audio_inputs += ["-stream_loop", "-1", "-i", str(music)]
            maps += ["-map", f"{audio_index}:a:0"]
            audio_index += 1
        final_cmd = [ffmpeg, "-y", "-i", str(silent), *audio_inputs]
        if narration is not None and music is not None:
            final_cmd += ["-filter_complex", "[1:a]volume=1.0[n];[2:a]volume=0.18[m];[n][m]amix=inputs=2:duration=first:dropout_transition=2[aout]", "-map", "0:v:0", "-map", "[aout]"]
        elif narration is not None or music is not None:
            final_cmd += ["-map", "1:a:0"]
        else:
            final_cmd += ["-an"]
        final_cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output)]
        subprocess.run(final_cmd, capture_output=True, text=True, check=True)
    return str(output)


def _resolve_scene_assets(plan: dict, asset_labels: list[str]) -> list[dict]:
    by_id: dict[str, Path] = {}
    for label in asset_labels:
        match = re.match(r"ASSET (\d+) = (.+)$", label)
        if match:
            by_id[f"ASSET {int(match.group(1)):02d}"] = MEDIA_ROOT / match.group(2)
    resolved: list[dict] = []
    for scene in plan.get("scenes", []):
        asset = str(scene.get("asset", "GENERATE")).strip().upper()
        path = by_id.get(asset)
        if path is None or not path.is_file():
            generated_name = f"generated_{uuid.uuid4().hex[:10]}.png"
            path = MEDIA_ROOT / generated_name
            generate_image(str(scene.get("visual_prompt") or "cinematic historical scene"), generated_name)
        resolved.append({**scene, "path": str(path)})
    return resolved


def _run_job(job_id: str, brief: str) -> None:
    try:
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        images = _media_images()
        audio = _media_audio()
        with tempfile.TemporaryDirectory(prefix="eva_catalog_") as catalog_dir:
            contact = Path(catalog_dir) / "contact.jpg"
            labels = _contact_sheet(images, contact)
            plan = _plan(brief, contact if labels else None, labels, [p.relative_to(MEDIA_ROOT).as_posix() for p in audio])
        scenes = _resolve_scene_assets(plan, labels)
        narration = MEDIA_ROOT / f"{_safe_name(plan.get('title'), 'video')}_narration.wav"
        _generate_narration(str(plan.get("narration", "")), narration)
        narration_duration = _duration_seconds(narration)
        if narration_duration > 0 and scenes:
            total = sum(max(1.5, float(s.get("duration", 3.0) or 3.0)) for s in scenes)
            factor = narration_duration / total
            for scene in scenes:
                scene["duration"] = max(1.5, float(scene.get("duration", 3.0) or 3.0) * factor)
        music = None
        if audio:
            music = audio[0]
        else:
            music = _generate_music(str(plan.get("music_prompt", "")), MEDIA_ROOT / f"{_safe_name(plan.get('title'), 'video')}_music.mp3")
        orientation = str(plan.get("orientation", "landscape")).lower()
        width, height = (SHORT_WIDTH, SHORT_HEIGHT) if orientation == "portrait" else (VIDEO_WIDTH, VIDEO_HEIGHT)
        output = MEDIA_ROOT / f"{_safe_name(plan.get('title'), 'eva_video')}.mp4"
        _render_scenes(scenes, output, width=width, height=height, narration=narration if narration.exists() else None, music=music)
        with _JOB_LOCK:
            _JOBS[job_id] = "completed"
        _notify({"job_id": job_id, "status": "completed", "path": str(output), "title": str(plan.get("title") or output.stem)})
    except Exception as exc:
        with _JOB_LOCK:
            _JOBS[job_id] = "failed"
        _notify({"job_id": job_id, "status": "failed", "error": str(exc)})


def start_media_production(brief: str) -> str:
    clean = str(brief or "").strip()
    if not clean:
        raise ValueError("Video tələbi boş ola bilməz.")
    job_id = f"media:{uuid.uuid4().hex[:12]}"
    with _JOB_LOCK:
        _JOBS[job_id] = "running"
    _notify({"job_id": job_id, "status": "started", "brief": clean})
    threading.Thread(target=_run_job, args=(job_id, clean), daemon=True, name=f"eva-media-{job_id[-6:]}").start()
    return job_id


def get_media_job(job_id: str) -> str:
    with _JOB_LOCK:
        return _JOBS.get(str(job_id).strip(), "unknown")
