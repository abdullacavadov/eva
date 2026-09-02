"""Optional WhatsApp Business Cloud API adapter.

Bu modul mövcud WhatsApp Web/Desktop axınından tam ayrıdır. Credentials yoxdursa
heç bir real API çağırışı etmir. Təhlükəsizlik üçün access token yalnız environment
də saxlanılır və heç vaxt nəticəyə daxil edilmir.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class WhatsAppBusinessError(RuntimeError):
    """Meta WhatsApp Cloud API xətası."""


def _config() -> tuple[str, str, str]:
    token = os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "").strip()
    api_version = os.getenv("WHATSAPP_CLOUD_API_VERSION", "v23.0").strip() or "v23.0"
    if not token or not phone_number_id:
        raise WhatsAppBusinessError(
            "Meta WhatsApp Cloud API konfiqurasiya edilməyib: "
            "WHATSAPP_CLOUD_ACCESS_TOKEN və WHATSAPP_CLOUD_PHONE_NUMBER_ID tələb olunur."
        )
    return token, phone_number_id, api_version


def build_text_payload(to: str, message: str) -> dict:
    to = str(to or "").strip()
    message = str(message or "").strip()
    if not to:
        raise ValueError("WhatsApp recipient tələb olunur.")
    if not message:
        raise ValueError("WhatsApp mesajı boş ola bilməz.")
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }


def send_text_message(to: str, message: str, *, timeout: float = 15.0) -> dict:
    token, phone_number_id, api_version = _config()
    payload = build_text_payload(to, message)
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = {"message": str(exc)}
        raise WhatsAppBusinessError(
            f"Meta WhatsApp API HTTP {exc.code}: {detail.get('error', detail).get('message', detail)}"
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise WhatsAppBusinessError(f"Meta WhatsApp API şəbəkə xətası: {exc}") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WhatsAppBusinessError("Meta WhatsApp API keçərsiz JSON qaytardı.") from exc

    messages = result.get("messages") or []
    message_id = messages[0].get("id", "") if messages else ""
    return {"status": "sent", "message_id": message_id}
