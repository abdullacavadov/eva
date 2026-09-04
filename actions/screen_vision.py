"""Ekran və aktiv webcam görüntüsü analizi."""

from __future__ import annotations

import ctypes
import io
import mimetypes
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from PIL import Image, ImageStat, ImageGrab

from app_config import get_app_config_value
from core.webcam_snapshot import LATEST_FRAME_PATH

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

VISION_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
)
VISION_MAX_DIMENSION = 1800
VISION_MAX_INLINE_BYTES = 5_500_000


def _get_active_window_title() -> str:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()
    except Exception:
        return ""


def _capture_active_window() -> tuple[bool, str, str]:
    window_title = _get_active_window_title()
    img = None
    capture_error = None

    if HAS_MSS:
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except Exception as exc:
            capture_error = exc

    if img is None:
        try:
            img = ImageGrab.grab(all_screens=True)
        except Exception as exc:
            detail = capture_error or exc
            return False, f"Ekran görüntüsü alınamadı: {detail}", ""

    try:
        handle = tempfile.NamedTemporaryFile(prefix="eva-screen-", suffix=".png", delete=False)
        tmp_path = Path(handle.name)
        handle.close()
        img.save(str(tmp_path), format="PNG")
    except Exception as exc:
        return False, f"Ekran görüntüsü kaydedilemedi: {exc}", ""
    return True, str(tmp_path), window_title


def _image_looks_blank(image_path: Path) -> bool:
    try:
        with Image.open(image_path) as img:
            sample = img.convert("RGB")
            stat = ImageStat.Stat(sample)
            means = stat.mean
            extrema = stat.extrema
            max_seen = max(channel[1] for channel in extrema)
            mean_total = sum(means) / max(1, len(means))
            return max_seen <= 8 or mean_total <= 3
    except Exception:
        return False


def _build_image_part(image_path: Path) -> types.Part:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/png"
    try:
        with Image.open(image_path) as img:
            work = img.copy()
        if work.mode not in {"RGB", "L"}:
            work = work.convert("RGB")
        if max(work.size) > VISION_MAX_DIMENSION:
            work.thumbnail((VISION_MAX_DIMENSION, VISION_MAX_DIMENSION), Image.Resampling.LANCZOS)
        png_buffer = io.BytesIO()
        work.save(png_buffer, format="PNG", optimize=True)
        png_bytes = png_buffer.getvalue()
        if len(png_bytes) <= VISION_MAX_INLINE_BYTES:
            return types.Part.from_bytes(data=png_bytes, mime_type="image/png")
        jpg_buffer = io.BytesIO()
        work.convert("RGB").save(jpg_buffer, format="JPEG", quality=88, optimize=True)
        return types.Part.from_bytes(data=jpg_buffer.getvalue(), mime_type="image/jpeg")
    except Exception:
        return types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)


def _vision_prompt(query: str, window_title: str) -> str:
    label = window_title or "aktiv pencere"
    user_query = (query or "Ekranda ne var?").strip()
    return (
        "Sen Windows üzerinde JARVIS için ekran analizi yapan bir görüntü yorumlayıcısısın.\n"
        "Aşağıdaki ekran görüntüsü aktif pencereye aittir.\n"
        f"Pencere başlığı: {label}\n\n"
        "Görevlerin:\n"
        "1. Pencerenin genel amacını 1-2 cümlede açıkla.\n"
        "2. Görünen önemli metinleri, hata mesajlarını, butonları, başlıkları ve durum etiketlerini oku.\n"
        "3. Kullanıcı sorusunu bu görüntüye göre doğrudan cevapla.\n"
        "4. Eğer bir hata, uyarı veya dikkat edilmesi gereken bir şey varsa bunu net belirt.\n"
        "5. Uydurma yapma. Emin olmadığın kısımlarda bunu söyle.\n\n"
        f"Kullanıcı sorusu: {user_query}\n\n"
        "Yanıtı Azərbaycan dilində ver. Gereksiz uzun olma."
    )


def _extract_response_text(response) -> str:
    try:
        text = str(getattr(response, "text", "") or "").strip()
    except Exception:
        text = ""
    if text:
        return text
    output_text = str(getattr(response, "output_text", "") or "").strip()
    if output_text:
        return output_text
    chunks: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = str(getattr(part, "text", "") or "").strip()
            if part_text:
                chunks.append(part_text)
    return "\n".join(chunks).strip()


def _response_diagnostic(response) -> str:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return "cavab namizədi yoxdur"
    reasons = []
    for candidate in candidates:
        reason = getattr(candidate, "finish_reason", None)
        if reason:
            reasons.append(str(reason))
    return ", ".join(reasons) if reasons else "mətn hissəsi yoxdur"


def _is_transient_vision_error(exc: Exception) -> bool:
    if isinstance(exc, (errors.ServerError, TimeoutError)):
        return True
    message = str(exc or "").lower()
    return any(marker in message for marker in (
        "503", "429", "deadline", "timed out", "timeout", "unavailable",
        "service unavailable", "internal error", "busy", "overloaded",
        "resource exhausted", "try again later", "backend error", "connection reset",
    ))


def _is_quota_vision_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    return any(marker in message for marker in (
        "quota", "rate limit", "resource exhausted", "too many requests",
        "quota exceeded", "limit exceeded", "billing",
    ))


def _friendly_vision_error(exc: Exception) -> str:
    if _is_quota_vision_error(exc):
        return "Gemini vision isteği kota veya hız limitinə takıldı."
    if _is_transient_vision_error(exc):
        return "Gemini vision servisi hazırda müvəqqəti əlçatmazdır."
    return f"Gemini vision isteği başarısız oldu: {exc}"


def _generate_vision_response(client, model_name: str, prompt: str, image_part: types.Part):
    """Generate a vision response through the SDK chat flow."""
    chat = client.chats.create(model=model_name)
    return chat.send_message([prompt, image_part])


def _analyze_with_gemini(client_query: str, image_path: Path, window_title: str) -> str:
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return "Gemini API açarı yoxdur."
    prompt = _vision_prompt(client_query, window_title)
    client = genai.Client(api_key=api_key)
    image_part = _build_image_part(image_path)
    retry_delays = (0.9, 1.8, 3.0)
    last_error: Exception | None = None
    for model_name in VISION_MODELS:
        for attempt, delay in enumerate(retry_delays, start=1):
            try:
                response = _generate_vision_response(client, model_name, prompt, image_part)
                merged = _extract_response_text(response)
                if merged:
                    return merged
                diagnostic = _response_diagnostic(response)
                last_error = RuntimeError(
                    f"Gemini {model_name} keçərli analiz mətni qaytarmadı ({diagnostic})."
                )
                if attempt < len(retry_delays):
                    time.sleep(delay)
                    continue
                break
            except Exception as exc:
                last_error = exc
                if attempt < len(retry_delays) and _is_transient_vision_error(exc):
                    time.sleep(delay)
                    continue
                if _is_transient_vision_error(exc):
                    break
                raise RuntimeError(_friendly_vision_error(exc)) from exc
    assert last_error is not None
    raise RuntimeError(_friendly_vision_error(last_error))


def _is_webcam_query(query: str) -> bool:
    q = (query or "").lower()
    markers = (
        "əlimdə", "elində", "əlimdəki", "əlimdə olan", "məni gör", "məni görür",
        "mənə bax", "kameraya bax", "kamerada nə", "qarşımdakı", "qarşımda nə",
        "gördüyün", "gördüklərin", "nə görürsən", "ne görürsən", "nə görürsən məni",
        "kamera ilə", "kameradan", "webcam",
    )
    return any(marker in q for marker in markers)


def _analyze_webcam_snapshot(query: str) -> str | None:
    if not LATEST_FRAME_PATH.exists() or LATEST_FRAME_PATH.stat().st_size <= 0:
        return None
    try:
        prompt = (
            "Sən EVA-nın webcam görmə modulusan. Bu şəkil EVA-nın aktiv webcam axınından "
            "alınmış son kadrdır. İstifadəçinin sualını yalnız şəkildə gördüklərinə əsasən "
            "cavablandır. Azərbaycan dilində danış. Obyektləri, insanları, rəngləri və vacib "
            "detalları dəqiq təsvir et. Əmin olmadığın şeyi fakt kimi təqdim etmə və heç nə uydurma.\n\n"
            f"İstifadəçinin sualı: {(query or 'Kamerada nə görürsən?').strip()}"
        )
        api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
        if not api_key:
            return "Gemini API açarı yoxdur."
        client = genai.Client(api_key=api_key)
        image_part = _build_image_part(LATEST_FRAME_PATH)
        last_error: Exception | None = None
        for model_name in VISION_MODELS:
            try:
                response = _generate_vision_response(client, model_name, prompt, image_part)
                text = _extract_response_text(response)
                if text:
                    return text
                last_error = RuntimeError(
                    f"Gemini {model_name} keçərli webcam analiz mətni qaytarmadı ({_response_diagnostic(response)})."
                )
            except Exception as exc:
                last_error = exc
                if _is_transient_vision_error(exc):
                    continue
                return _friendly_vision_error(exc)
        return _friendly_vision_error(last_error or RuntimeError("Vision modeli cavab vermədi."))
    except Exception as exc:
        return f"Webcam görüntüsü analiz edilə bilmədi: {exc}"


def analyze_screen(query: str, target: str = "active_window") -> str:
    if _is_webcam_query(query):
        webcam_result = _analyze_webcam_snapshot(query)
        if webcam_result is not None:
            return webcam_result

    ok, result, window_title = _capture_active_window()
    if not ok:
        return f"Ekran görüntüsü alınamadı: {result}"

    image_path = Path(result)
    try:
        if not image_path.exists():
            return "Ekran görüntüsü dosyası bulunamadı. Tekrar dene."
        if image_path.stat().st_size <= 0:
            return "Ekran görüntüsü boş geldi."
        if _image_looks_blank(image_path):
            return "Ekran görüntüsü siyah və ya boş görünüyor."
        try:
            analysis = _analyze_with_gemini(query, image_path, window_title)
        except Exception as exc:
            prefix = window_title.strip()
            if prefix:
                return f"Ekran görüntüsü alındı ({prefix}) ama analiz tamamlanamadı: {exc}"
            return f"Ekran görüntüsü alındı ama analiz tamamlanamadı: {exc}"
        if window_title:
            return f"[Aktif pencere: {window_title}]\n{analysis}"
        return analysis
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass