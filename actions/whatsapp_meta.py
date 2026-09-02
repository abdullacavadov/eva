"""Meta WhatsApp Business Cloud API action adapter."""

from __future__ import annotations

from integrations.whatsapp.meta_business import send_text_message


def send_whatsapp_business_message(message: str, phone_number: str) -> dict:
    """Meta Cloud API ilə mətn mesajı göndərir; göndəriş özü ayrıca confirmation gate-dən keçir."""
    result = send_text_message(phone_number, message)
    return {"type": "whatsapp", "status": "success", "data": [{"id": f"whatsapp:{result['message_id']}", "message_id": result["message_id"], "to": phone_number, "status": result["status"], "provider": "meta_cloud"}], "count": 1, "selected": None, "meta": {"provider": "meta_cloud"}}
