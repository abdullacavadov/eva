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
    """JSON payload ilə media slideshow yaradır."""
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
    if os.name != "nt":
        raise RuntimeError("Media qovluğunu avtomatik açmaq yalnız Windows-da dəstəklənir.")
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
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


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not query.strip():
        return "Çalınacaq və ya yaradılacaq məzmun göstərilməyib."

    normalized_provider = (provider or "auto").strip().lower()

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


# Media action artıq yaradılmanı və lokal media idarəsini dəstəkləyir.
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
            "Gemini ilə şəkil yaradır, mövcud media fayllarını siyahılayır, "
            "şəkillərdən FFmpeg slideshow videosu hazırlayır və lokal videonu açır. "
            "Mahnı/video çalmaq üçün provider=auto|youtube|spotify. "
            "Yeni şəkil yaratmaq üçün provider=image və query-də image prompt ver. "
            "Slideshow üçün provider=slideshow və JSON payload ver: "
            "{images:[...],filename,seconds_per_image,title_text,music_path,music_volume}. "
            "Slideshow yaratmazdan əvvəl şəkillərin adlarını bilmirsənsə provider=list_media çağır "
            "və qaytarılan fayl siyahısından uyğun şəkilləri seç. "
            "Slideshow uğurla bitəndə media qovluğu avtomatik açılır. "
            "İstifadəçi 'videonu aç', 'göstər', 'baxım' kimi lokal videoya baxmaq istədiyini deyirsə "
            "provider=open_video istifadə et və query-də video adını ver; uzantı yoxdursa özü tapacaq. "
            "Media qovluğunu ayrıca açmaq üçün provider=open_folder istifadə et. "
            "İstifadəçi media yaratmağı istədikdə playback provider seçmə."
        )
        declaration["parameters"]["properties"]["provider"]["description"] = (
            "auto | youtube | spotify | image | slideshow | list_media | open_video | open_folder. "
            "image şəkil generasiyası, slideshow şəkillərdən video yaradılması, "
            "list_media media fayllarının siyahısı, open_video lokal videonun açılması, "
            "open_folder media qovluğunun açılması üçündür."
        )
        return


_register_media_tool_capabilities()
