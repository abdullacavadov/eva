"""
Medya oynatma və yaradılması — Windows üçün YouTube, Spotify və EVA media pipeline.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.parse
import webbrowser

from actions.browser import browser_control
from actions.media_creation import create_media_slideshow, generate_media_image

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
    """JSON payload ilə media slideshow yaradır.

    Payload:
    {"images":["a.png","b.jpg"],"filename":"video.mp4",
     "seconds_per_image":3,"title_text":"","music_path":"","music_volume":0.22}
    """
    try:
        payload = json.loads(query)
    except json.JSONDecodeError as exc:
        raise ValueError("Slideshow üçün JSON media parametrləri tələb olunur.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Slideshow parametrləri obyekt olmalıdır.")
    images = payload.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("Slideshow üçün ən azı bir şəkil tələb olunur.")
    return create_media_slideshow(
        [str(item) for item in images],
        str(payload.get("filename", "slideshow.mp4")),
        seconds_per_image=float(payload.get("seconds_per_image", 3.0)),
        title_text=str(payload.get("title_text", "")),
        music_path=str(payload.get("music_path", "")),
        music_volume=float(payload.get("music_volume", 0.22)),
    )


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not query.strip():
        return "Çalınacaq və ya yaradılacaq məzmun göstərilməyib."

    normalized_provider = (provider or "auto").strip().lower()

    # Phase 10.2: media creation is exposed through the existing media action
    # to avoid changing the ToolExecutor dispatch contract in this phase.
    if normalized_provider in {"image", "generate_image", "image_generation"}:
        return f"Şəkil hazırlandı: {_create_image(query)}"
    if normalized_provider in {"slideshow", "video", "create_video"}:
        return f"Video hazırlandı: {_create_slideshow(query)}"

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
