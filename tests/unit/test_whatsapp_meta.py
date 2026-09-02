import pytest

from integrations.whatsapp.meta_business import (
    WhatsAppBusinessError,
    _config,
    build_text_payload,
)


def test_build_text_payload_is_meta_compatible():
    payload = build_text_payload("994501234567", "Salam")
    assert payload == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "994501234567",
        "type": "text",
        "text": {"preview_url": False, "body": "Salam"},
    }


@pytest.mark.parametrize("to,message", [("", "Salam"), ("994501234567", "")])
def test_build_text_payload_rejects_empty_values(to, message):
    with pytest.raises(ValueError):
        build_text_payload(to, message)


def test_cloud_api_requires_credentials(monkeypatch):
    monkeypatch.delenv("WHATSAPP_CLOUD_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", raising=False)
    with pytest.raises(WhatsAppBusinessError):
        _config()
