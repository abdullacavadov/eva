"""
Tarayıcı kontrolü — Windows için webbrowser modülü ile çalışır.
"""

import re
import subprocess
import urllib.parse
import webbrowser

import requests

_VIDEO_ID_RE = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def _open(url: str) -> None:
    webbrowser.open(url)


def _find_first_youtube_video(query: str) -> str | None:
    encoded = urllib.parse.quote_plus(query)
    response = requests.get(
        f"https://www.youtube.com/results?search_query={encoded}",
        headers={"User-Agent": "EVA/1.0"},
        timeout=10,
    )
    response.raise_for_status()

    seen: set[str] = set()
    for video_id in _VIDEO_ID_RE.findall(response.text):
        if video_id not in seen:
            seen.add(video_id)
            return video_id
    return None


def _open_traffic_map(origin: str, destination: str) -> str:
    if not origin or not destination:
        return "Trafik üçün başlanğıc və təyinat məkanı lazımdır."
    params = urllib.parse.urlencode({"api": "1", "origin": origin, "destination": destination, "travelmode": "driving"})
    url = f"https://www.google.com/maps/dir/?{params}"
    _open(url)
    return (
        f"{origin} ilə {destination} arasında sürücülük marşrutunu Google Maps-də açdım. "
        "Canlı trafik sıxlığı və gecikmələr xəritədə göstərilir."
    )


def _open_city_traffic(location: str) -> str:
    if not location:
        return "Trafik üçün şəhər və ya məkan adı lazımdır."
    params = urllib.parse.urlencode({"api": "1", "query": f"traffic {location}"})
    url = f"https://www.google.com/maps/search/?{params}"
    _open(url)
    return f"{location} üçün Google Maps trafik görünüşünü açdım. Canlı sıxlıq xəritədə göstərilir."


def browser_control(action: str, url: str = None, query: str = None) -> str:
    action = str(action or "").strip().lower()
    if action == "open_url":
        if not url:
            return "URL belirtilmedi."
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        _open(url)
        return f"Açıldı: {url}"

    elif action == "search":
        if not query:
            return "Arama sorgusu belirtilmedi."
        encoded = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        _open(search_url)
        return f"'{query}' için arama açıldı."

    elif action in ("play_youtube", "youtube_play", "play_music"):
        if not query:
            return "YouTube için arama sorgusu belirtilmedi."

        try:
            video_id = _find_first_youtube_video(query)
        except Exception as exc:
            encoded = urllib.parse.quote(query)
            fallback_url = f"https://www.youtube.com/results?search_query={encoded}"
            _open(fallback_url)
            return (
                f"YouTube ilk sonucu alınamadı ({exc}). "
                f"Arama sonuçları açıldı: {query}"
            )

        if not video_id:
            encoded = urllib.parse.quote(query)
            fallback_url = f"https://www.youtube.com/results?search_query={encoded}"
            _open(fallback_url)
            return f"YouTube'da doğrudan video bulunamadı. Arama sonuçları açıldı: {query}"

        watch_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        _open(watch_url)
        return f"YouTube'da oynatılıyor: {query}"

    elif action in ("traffic", "get_traffic", "route"):
        text = str(query or "").strip()
        parts = re.split(r"\s*(?:->|→|\bto\b|\b-dan\s+|-dən\s+)\s*", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            return _open_traffic_map(parts[0].strip(), parts[1].strip())
        return _open_city_traffic(text)

    return f"Bilinmeyen eylem: {action}"
