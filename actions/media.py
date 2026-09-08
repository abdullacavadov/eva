"""
Medya oynatma və yaradılması — Windows üçün YouTube, Spotify və EVA media pipeline.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path

from actions.browser import browser_control
from actions.media_creation import (
    MEDIA_ROOT,
    create_media_slideshow,
    generate_media_image,
    list_media_files,
    resolve_media_video,
)
from core.media_producer import get_media_job, set_job_notifier, start_media_production

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

_MEDIA_JOBS: dict[str, dict] = {}


def _copy_to_clipboard(text: str) -> tuple[bool, str]:
    if HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return True, "ok"
        except Exception as exc:
            return False, f"Panoya kopyalanamadı: {exc}"
    try:
        subprocess.run(
            ["powershell", "-Command", f"Set-Clipboard -Value '{text.replace(chr(39), chr(96))}'"],
            check=True, timeout=5,
        )
        return True, "ok"
    except Exception as exc:
        return False, f"Panoya kopyalanamadı: {exc}"


def _spotify_installed() -> bool:
    return shutil.which("Spotify") is not None or subprocess.run(
        ["where", "Spotify"], shell=False, capture_output=True
    ).returncode == 0


def _play_youtube(query: str) -> str:
    return browser_control("play_youtube", query=query)


def _play_spotify(query: str, autoplay: bool = True) -> str:
    encoded_query = urllib.parse.quote(query.strip())
    search_url = f"spotify:search:{encoded_query}"
    try:
        webbrowser.open(search_url)
    except Exception as exc:
        return f"Spotify açılamadı: {exc}"
    return f"Spotify'da '{query}' araması açıldı."


def _create_image(query: str) -> str:
    prompt = query.strip()
    if not prompt:
        raise ValueError("Şəkil prompt-u boş ola bilməz.")
    return generate_media_image(prompt, "generated.png")


def _create_slideshow(query: str) -> str:
    """JSON payload ilə legacy slideshow yaradır."""
    try:
        payload = json.loads(query)
    except json.JSONDecodeError as exc:
        raise ValueError("Slideshow üçün JSON media parametrləri tələb olunur.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Slideshow parametrləri obyekt olmalıdır.")
    images = payload.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("Slideshow üçün ən azı bir şəkil tələb olunur.")
    output = create_media_slideshow(
        [str(item) for item in images],
        str(payload.get("filename", "slideshow.mp4")),
        seconds_per_image=float(payload.get("seconds_per_image", 3.0)),
        title_text=str(payload.get("title_text", "")),
        music_path=str(payload.get("music_path", "")),
        music_volume=float(payload.get("music_volume", 0.22)),
    )
    _open_media_folder()
    return output


def _open_media_folder() -> str:
    """Windows Explorer-də EVA media qovluğunu açır."""
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(MEDIA_ROOT))
    return str(MEDIA_ROOT)


def _latest_media_video():
    videos = sorted(
        (item for item in MEDIA_ROOT.rglob("*.mp4") if item.is_file()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return videos[0] if videos else None


def _open_video(query: str) -> str:
    """Lokal videonu standart Windows media player ilə açır."""
    if os.name != "nt":
        raise RuntimeError("Video faylını avtomatik açmaq yalnız Windows-da dəstəklənir.")
    clean_query = query.strip()
    generic = clean_query.casefold() in {"", "video", "videonu", "videonu göstər", "videonu goster", "göstər", "goster", "baxım", "baxim", "bax"}
    video = _latest_media_video() if generic else resolve_media_video(clean_query)
    if video is None or not video.is_file():
        raise FileNotFoundError("Media qovluğunda açılacaq video tapılmadı.")
    os.startfile(str(video))
    return f"Video açıldı: {video}"


def _close_media_player() -> str:
    """Yalnız Windows Media Player proseslərini bağlayır; ümumi shell/taskkill açmır."""
    if os.name != "nt":
        raise RuntimeError("Media Player-i avtomatik bağlama yalnız Windows-da dəstəklənir.")
    result = subprocess.run(
        [
            "powershell", "-NoProfile", "-Command",
            "Get-Process -Name wmplayer,MediaPlayer -ErrorAction SilentlyContinue | Stop-Process -Force",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in {0}:
        raise RuntimeError("Media Player bağlana bilmədi.")
    return "Media Player bağlandı."


def _play_background_notification_sfx() -> None:
    """Media prodakşn başlayanda SFX/Start.mp3 faylını səssizcə başladır."""
    if os.name != "nt":
        return
    start_sound = Path(__file__).resolve().parent.parent / "SFX" / "Start.mp3"
    if not start_sound.is_file():
        return
    try:
        os.startfile(str(start_sound))
    except Exception:
        pass


def _remember_media_job(job_id: str, query: str) -> None:
    _MEDIA_JOBS[job_id] = {"brief": query, "started_at": time.time()}


def _production_stage(job_id: str) -> tuple[str, int]:
    """Mövcud artefaktlardan istifadə edib canlı prodakşn mərhələsini göstərir.

    Pipeline-ın daxili thread-i dəyişdirilmədən status müşahidə olunur; buna görə
    status göstəricisi heç vaxt saxta dəqiq progress iddiası etmir.
    """
    job = _MEDIA_JOBS.get(job_id, {})
    started_at = float(job.get("started_at", 0.0) or 0.0)
    status = get_media_job(job_id)
    if status == "completed":
        return "Tamamlandı", 100
    if status == "failed":
        return "Xəta baş verdi", 0

    recent = []
    try:
        recent = [
            path for path in MEDIA_ROOT.rglob("*")
            if path.is_file() and (not started_at or path.stat().st_mtime >= started_at)
        ]
    except OSError:
        pass

    generated_images = [p for p in recent if p.name.startswith("generated_") and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    narration = [p for p in recent if p.name.endswith("_narration.wav")]
    music = [p for p in recent if p.name.endswith("_music.mp3")]
    videos = [p for p in recent if p.suffix.lower() == ".mp4"]

    if videos:
        return "Final video renderi tamamlanır", 95
    if narration:
        if music:
            return "FFmpeg final renderi hazırlanır", 85
        return "Musiqi hazırlanır və ya seçilir", 75
    if generated_images:
        return f"Gemini vizualları yaradır — {len(generated_images)} şəkil hazırdır", 50
    return "Mövzu analiz edilir və vizuallar seçilir", 20


def _media_production_status(query: str = "") -> str:
    """Aktiv və ya son video prodakşn işinin canlı statusunu qaytarır."""
    job_id = query.strip()
    current_project_aliases = {
        "current_video_project",
        "current_video",
        "current_media_project",
        "current_media",
        "latest_video",
        "latest_media",
    }
    if job_id.casefold() in current_project_aliases:
        job_id = ""
    if not job_id:
        if not _MEDIA_JOBS:
            return "Hazırda izlənən video prodakşn işi yoxdur."
        job_id = next(reversed(_MEDIA_JOBS))
    if job_id not in _MEDIA_JOBS:
        return f"Bu video prodakşn işi tapılmadı: {job_id}"

    stage, progress = _production_stage(job_id)
    job = _MEDIA_JOBS[job_id]
    elapsed = max(0, int(time.time() - float(job.get("started_at", time.time()))))
    minutes, seconds = divmod(elapsed, 60)
    elapsed_text = f"{minutes} dəq {seconds} san" if minutes else f"{seconds} san"
    status = get_media_job(job_id)
    brief = str(job.get("brief", "")).strip()
    bar_units = 20
    filled = min(bar_units, round(progress / 100 * bar_units))
    bar = "█" * filled + "░" * (bar_units - filled)
    return (
        f"🎬 VİDEO PRODÜKSİYASI\n"
        f"{bar} {progress}%\n"
        f"İş: {job_id}\n"
        f"Sorğu: {brief}\n"
        f"Mərhələ: {stage}\n"
        f"Status: {status}\n"
        f"Keçən vaxt: {elapsed_text}"
    )


def _media_job_ui_event(event: dict) -> None:
    """Arxa plan media işinin statusunu və tamamlanmasını bildirir."""
    status = str(event.get("status", "")).lower()
    if status == "started":
        job_id = str(event.get("job_id", "")).strip()
        if job_id:
            _remember_media_job(job_id, str(event.get("brief", "")))
        _play_background_notification_sfx()
        return
    if status == "completed":
        _open_media_folder()
        return


set_job_notifier(_media_job_ui_event)


def _looks_like_video_creation_request(query: str) -> bool:
    text = str(query or "").casefold()
    creation = ("hazırla", "hazirla", "yarat", "yaratmaq", "düzəlt", "duzelt", "hazırlamaq", "hazirlamaq")
    video_terms = ("video", "short", "youtube", "slayd-şou", "slideshow", "rolik")
    return any(item in text for item in creation) and any(item in text for item in video_terms)


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    normalized_provider = (provider or "auto").strip().lower()

    if normalized_provider in {"production_status", "media_status", "video_status", "status"}:
        return _media_production_status(query)

    if not query or not query.strip():
        return "Çalınacaq və ya yaradılacaq məzmun göstərilməyib."

    if normalized_provider in {"production", "media_production", "create_production_video", "video_production"}:
        job_id = start_media_production(query)
        _remember_media_job(job_id, query)
        return f"Video prodakşn işi başladıldı: {job_id}. Arxa planda davam edir; E.V.A digər əmrləri qəbul edə bilər."

    if normalized_provider == "auto" and _looks_like_video_creation_request(query):
        job_id = start_media_production(query)
        _remember_media_job(job_id, query)
        return f"Video prodakşn işi başladıldı: {job_id}. Arxa planda davam edir; E.V.A digər əmrləri qəbul edə bilər."

    if normalized_provider in {"image", "generate_image", "image_generation"}:
        return f"Şəkil hazırlandı: {_create_image(query)}"
    if normalized_provider in {"slideshow", "video", "create_video"}:
        return f"Video hazırlandı: {_create_slideshow(query)}"
    if normalized_provider in {"open_video", "video_open", "play_local_video", "local_video"}:
        return _open_video(query)
    if normalized_provider in {"close_media_player", "close_player", "stop_media_player"}:
        return _close_media_player()
    if normalized_provider in {"list", "list_media", "media_list", "files"}:
        files = list_media_files()
        return "Media faylları: " + (", ".join(files) if files else "media qovluğu boşdur.")
    if normalized_provider in {"open_folder", "media_folder", "folder"}:
        return f"Media qovluğu açıldı: {_open_media_folder()}"

    if normalized_provider in {"yt", "youtube music"}:
        normalized_provider = "youtube"
    elif normalized_provider in {"apple music", "music", "apple_music"}:
        return _play_youtube(query)

    if normalized_provider == "spotify":
        return _play_spotify(query, autoplay=autoplay)
    if normalized_provider == "youtube":
        return _play_youtube(query)

    result = _play_spotify(query, autoplay=autoplay)
    if "açılamadı" not in result:
        return result
    return _play_youtube(query)


# Media action yaradılmanı, lokal media idarəsini və avtonom video prodakşnını dəstəkləyir.
def _register_media_tool_capabilities() -> None:
    try:
        import tool_defs
    except ImportError:
        return

    for declaration in tool_defs.TOOL_DECLARATIONS:
        if declaration.get("name") != "play_media":
            continue
        declaration["description"] = (
            "Media əməliyyatlarını yerinə yetirir: YouTube/Spotify-da məzmun açır, "
            "Gemini ilə şəkil yaradır, lokal media fayllarını idarə edir və peşəkar video prodakşnı başladır. "
            "YouTube Short və ya böyük video kimi video yaratma tələblərində provider=production istifadə et; "
            "query-də yalnız istifadəçinin təbii video tələbi olsun. Production arxa planda işləyir, "
            "lokal şəkilləri fayl adına görə kor-koranə seçmir: Gemini kontakt vərəqini vizual olaraq analiz edir, "
            "uyğun aktivləri seçir və çatışmayan səhnələr üçün Gemini şəkil yaradır. "
            "Ssenari, narrasiya, keçidlər, ekrandakı mətn, musiqi və FFmpeg renderi avtomatik planlanır. "
            "İstifadəçi 'video nə yerdədir?', 'proses necə gedir?' və ya 'video prosesini göstər' deyirsə provider=production_status istifadə et; "
            "query boşdursa son başladılan video işinin canlı statusunu qaytar. Konkret job ID verilərsə həmin işi göstər. "
            "Status dəqiq olmayan faiz uydurmur; mərhələ və müşahidə olunan artefaktlara əsaslanan təxmini progress göstərir. "
            "İstifadəçi sadə slideshow istəyirsə provider=slideshow və JSON payload istifadə et. "
            "İstifadəçi 'videonu aç', 'göstər', 'baxım' deyirsə provider=open_video istifadə et; "
            "query konkret ad vermirsə ən son yaradılmış MP4 açılır. "
            "İstifadəçi 'Media Player-ı bağla' deyirsə provider=close_media_player istifadə et. "
            "Media qovluğunu ayrıca açmaq üçün provider=open_folder istifadə et."
        )
        declaration["parameters"]["properties"]["provider"]["description"] = (
            "auto | youtube | spotify | image | production | production_status | slideshow | list_media | open_video | "
            "close_media_player | open_folder. production peşəkar, avtonom YouTube video hazırlamaq üçündür və arxa planda işləyir; "
            "production_status canlı mərhələ/progress məlumatını göstərir."
        )
        return


_register_media_tool_capabilities()
