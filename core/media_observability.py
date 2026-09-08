"""Media production üçün canlı mərhələ və UI müşahidə qatı."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from core import media_producer as mp
from core.media_video_provider import is_fal_video_enabled, render_video_scenes

_INSTALLED = False
_CURRENT_JOB = ""
_ORIGINAL_NOTIFY = None


def _emit(stage: str, *, progress: int, message: str, **payload: Any) -> None:
    if not _CURRENT_JOB:
        return
    mp._notify({
        "status": "running",
        "job_id": _CURRENT_JOB,
        "stage": stage,
        "progress": progress,
        "message": message,
        **payload,
    })


def _is_retryable_planner_error(exc: Exception) -> bool:
    """Gemini-nin müvəqqəti overload/rate-limit xətalarını müəyyən edir."""
    text = str(exc).upper()
    return any(marker in text for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))


def _plan_with_retry(plan_fn, brief, contact_sheet, asset_labels, audio_labels):
    """Planner üçün yalnız transient Gemini xətalarında qısa retry edir."""
    for attempt in range(3):
        try:
            return plan_fn(brief, contact_sheet, asset_labels, audio_labels)
        except Exception as exc:
            if attempt == 2 or not _is_retryable_planner_error(exc):
                raise
            time.sleep(2 ** attempt)


def install(bridge) -> None:
    """Media producer funksiyalarını dəyişdirmədən observability əlavə edir."""
    global _INSTALLED, _ORIGINAL_NOTIFY
    if _INSTALLED:
        return
    _INSTALLED = True

    original_notify = mp._notify
    _ORIGINAL_NOTIFY = original_notify

    def notify(event: dict) -> None:
        global _CURRENT_JOB
        status = str(event.get("status", "")).lower()
        job_id = str(event.get("job_id", "")).strip()
        if status == "started" and job_id:
            _CURRENT_JOB = job_id
            bridge.emit("media.production", data={
                "job_id": job_id,
                "status": "running",
                "stage": "queued",
                "progress": 2,
                "message": "Video prodakşn işi qəbul edildi.",
            })
        elif status == "running" and job_id and event.get("stage"):
            bridge.emit("media.production", data={
                "job_id": job_id,
                "status": "running",
                "stage": str(event.get("stage", "")),
                "progress": int(event.get("progress", 0) or 0),
                "message": str(event.get("message", "")).strip(),
                **{
                    key: value
                    for key, value in event.items()
                    if key not in {"status", "job_id", "stage", "progress", "message"}
                },
            })
        elif status == "completed" and job_id:
            bridge.emit("media.production", data={
                "job_id": job_id,
                "status": "completed",
                "stage": "completed",
                "progress": 100,
                "message": "Video hazırdır.",
                "provider": "fal.ai / LTX-2.3" if is_fal_video_enabled() else "FFmpeg",
            })
            _CURRENT_JOB = ""
        elif status == "failed" and job_id:
            bridge.emit("media.production", data={
                "job_id": job_id,
                "status": "failed",
                "stage": "failed",
                "progress": 0,
                "message": "Video prodakşnı uğursuz oldu.",
                "error": str(event.get("error", "")).strip(),
            })
            _CURRENT_JOB = ""
        original_notify(event)

    mp._notify = notify

    original_plan = mp._plan

    def plan(brief: str, contact_sheet, asset_labels, audio_labels):
        _emit("transcribing", progress=8, message="Mövzu üzrə transkripsiya və narrasiya hazırlanır.")
        _emit("planning_scenes", progress=16, message="Səhnə quruluşu və vizual tələblər müəyyənləşdirilir.")
        result = _plan_with_retry(original_plan, brief, contact_sheet, asset_labels, audio_labels)
        scenes = result.get("scenes", []) if isinstance(result, dict) else []
        transcript = str(result.get("narration", "")) if isinstance(result, dict) else ""
        _emit("transcript_ready", progress=24, message="Transkripsiya hazırdır.", transcript=transcript)
        _emit(
            "scenes_ready",
            progress=30,
            message=f"{len(scenes)} səhnə müəyyən edildi.",
            transcript=transcript,
            scenes=[
                {
                    "index": index,
                    "asset": str(scene.get("asset", "GENERATE")),
                    "text": str(scene.get("onscreen_text", "")),
                    "visual_prompt": str(scene.get("visual_prompt", "")),
                    "duration": float(scene.get("duration", 0) or 0),
                    "generated": str(scene.get("asset", "")).upper() == "GENERATE",
                }
                for index, scene in enumerate(scenes)
            ],
        )
        return result

    mp._plan = plan

    original_resolve = mp._resolve_scene_assets

    def resolve(plan_data: dict, asset_labels: list[str]):
        _emit("analyzing_assets", progress=36, message=f"{len(asset_labels)} lokal vizual analiz edilir.")
        _emit("selecting_assets", progress=42, message="Səhnələr üçün uyğun vizuallar seçilir.")
        scenes = plan_data.get("scenes", [])
        missing = sum(1 for scene in scenes if str(scene.get("asset", "GENERATE")).upper() == "GENERATE")
        if missing:
            _emit("generating_missing_images", progress=48, message=f"{missing} səhnə üçün Gemini vizualı yaradılacaq.")
        resolved = original_resolve(plan_data, asset_labels)
        return resolved

    mp._resolve_scene_assets = resolve

    original_narration = mp._generate_narration

    def narration(text: str, destination: Path):
        _emit("generating_voice", progress=70, message="Narrasiya hazırlanır.")
        return original_narration(text, destination)

    mp._generate_narration = narration

    original_music = mp._generate_music

    def music(prompt: str, destination: Path):
        _emit("generating_music", progress=78, message="Musiqi seçilir və ya yaradılır.")
        return original_music(prompt, destination)

    mp._generate_music = music

    original_render = mp._render_scenes

    def render(scenes, output, *, width, height, narration, music):
        _emit("generating_video", progress=56, message="AI video səhnələri hazırlanır.", provider="fal.ai / LTX-2.3" if is_fal_video_enabled() else "FFmpeg")
        if is_fal_video_enabled():
            return render_video_scenes(
                scenes,
                output,
                width=width,
                height=height,
                narration=narration,
                music=music,
                on_update=lambda message, progress: _emit("generating_video", progress=progress, message=message),
            )
        _emit("rendering", progress=84, message="Lokal səhnələr FFmpeg ilə render edilir.")
        return original_render(scenes, output, width=width, height=height, narration=narration, music=music)

    mp._render_scenes = render
