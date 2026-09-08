"""
Medya oynatma və yaradılması — Windows üçün YouTube, Spotify və EVA media pipeline.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.parse
import webbrowser

from actions.browser import browser_control
from actions.media_creation import (
    MEDIA_ROOT,
    create_media_slideshow,
    generate_media_image,
    list_media_files,
    resolve_media_video,
)
from core.media_producer import set_job_notifier, start_media_production

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


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


def _open_video(query: str) -> str:
    """Media qovluğundakı videonu standart Windows media player ilə açır."""
    if os.name != "nt":
        raise RuntimeError("Video faylını avtomatik açmaq yalnız Windows-da dəstəklənir.")
    video = resolve_media_video(query.strip())
    if not video.is_file():
        raise FileNotFoundError(f"Video tapılmadı: {video}")
    os.startfile(str(video))
    return f"Video açıldı: {video}"


def _media_job_ui_event(event: dict) -> None:
    """Arxa plan media işini mövcud EVA UI-a təhlükəsiz şəkildə çatdırır."""
    try:
        import tkinter as tk
        root = getattr(tk, "_default_root", None)
        if root is None:
            return
        status = str(event.get("status", "")).lower()

        def apply_event():
            ui = getattr(root, "_jarvis_ui", None)
            if ui is None:
                return
            if status == "started":
                ui.set_state("Video Generasiya olunur")
                ui.write_log("SYS: Video Generasiya olunur. Bu vaxt E.V.A digər əmrləri qəbul edir.")
            elif status == "completed":
                path = str(event.get("path", ""))
                ui.set_state("LISTENING")
                ui.write_log(f"SYS: Video hazırdır — {path}")
                _open_media_folder()
            elif status == "failed":
                ui.set_state("ERROR")
                ui.write_log(f"ERR: Video generasiyası uğursuz oldu — {event.get('error', 'naməlum xəta')}")

        root.after(0, apply_event)
    except Exception:
        pass


set_job_notifier(_media_job_ui_event)


def _looks_like_video_creation_request(query: str) -> bool:
    text = str(query or "").casefold()
    creation = ("hazırla", "hazirla", "yarat", "yaratmaq", "düzəlt", "duzelt", "hazırlamaq", "hazirlamaq")
    video_terms = ("video", "short", "youtube", "slayd-şou", "slideshow", "rolik")
    return any(item in text for item in creation) and any(item in text for item in video_terms)


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not query.strip():
        return "Çalınacaq və ya yaradılacaq məzmun göstərilməyib."

    normalized_provider = (provider or "auto").strip().lower()

    if normalized_provider in {"production", "media_production", "create_production_video", "video_production"}:
        job_id = start_media_production(query)
        return f"Video prodakşn işi başladıldı: {job_id}. Arxa planda davam edir; E.V.A digər əmrləri qəbul edə bilər."

    if normalized_provider == "auto" and _looks_like_video_creation_request(query):
        job_id = start_media_production(query)
        return f"Video prodakşn işi başladıldı: {job_id}. Arxa planda davam edir; E.V.A digər əmrləri qəbul edə bilər."

    if normalized_provider in {"image", "generate_image", "image_generation"}:
        return f"Şəkil hazırlandı: {_create_image(query)}"
    if normalized_provider in {"slideshow", "video", "create_video"}:
        return f"Video hazırlandı: {_create_slideshow(query)}"
    if normalized_provider in {"open_video", "video_open", "play_local_video", "local_video"}:
        return _open_video(query)
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
# ToolExecutor dəyişdirilmir: mövcud play_media dispatch müqaviləsi qorunur.
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
            "İstifadəçi sadə slideshow istəyirsə provider=slideshow və JSON payload istifadə et. "
            "İstifadəçi 'videonu aç', 'göstər', 'baxım' deyirsə provider=open_video istifadə et. "
            "Media qovluğunu ayrıca açmaq üçün provider=open_folder istifadə et."
        )
        declaration["parameters"]["properties"]["provider"]["description"] = (
            "auto | youtube | spotify | image | production | slideshow | list_media | open_video | open_folder. "
            "production peşəkar, avtonom YouTube video hazırlamaq üçündür və arxa planda işləyir."
        )
        return


_register_media_tool_capabilities()
