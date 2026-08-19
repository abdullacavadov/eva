from unittest.mock import MagicMock, patch

from actions import whatsapp


def test_normalize_phone_keeps_international_number():
    assert whatsapp._normalize_phone("+994 50 123 45 67") == "994501234567"


def test_normalize_lookup_is_case_and_diacritic_insensitive():
    assert whatsapp._normalize_lookup("İSMAYIL") == "ismayil"


def test_find_contact_matches_alias(monkeypatch):
    monkeypatch.setattr(
        whatsapp,
        "_load_contacts",
        lambda: {
            "ehmed": {
                "display_name": "Əhməd",
                "value": "+994501234567",
                "aliases": ["Ami"],
            }
        },
    )
    monkeypatch.setattr(whatsapp, "_load_phone_book", lambda: {})

    contact = whatsapp._find_contact("Ami")

    assert contact is not None
    assert contact["display_name"] == "Əhməd"
    assert contact["value"] == "+994501234567"


def test_find_contact_returns_none_for_unknown_contact(monkeypatch):
    monkeypatch.setattr(
        whatsapp,
        "_load_contacts",
        lambda: {
            "ehmed": {
                "display_name": "Əhməd",
                "value": "+994501234567",
            }
        },
    )
    monkeypatch.setattr(whatsapp, "_load_phone_book", lambda: {})

    assert whatsapp._find_contact("Tanınmayan şəxs") is None


def test_save_contact_rejects_invalid_phone():
    result = whatsapp.save_whatsapp_contact("Test", "123")

    assert "Telefon nömrəsi" in result


def test_send_message_requires_message():
    assert whatsapp.send_whatsapp_message("   ") == "Mesaj boş ola bilməz."


def test_send_message_requires_recipient_when_phone_missing(monkeypatch):
    monkeypatch.setattr(whatsapp, "_find_contact", lambda _: None)

    result = whatsapp.send_whatsapp_message(
        "Salam",
        recipient_name="Naməlum şəxs",
    )

    assert "telefon nömrəsi tapılmadı" in result


def test_draft_does_not_run_automatic_send(monkeypatch):
    monkeypatch.setattr(whatsapp, "HAS_PYAUTOGUI", True)
    monkeypatch.setattr(
        whatsapp,
        "_open_whatsapp_desktop_via_scheme",
        MagicMock(return_value=(True, "WhatsApp Desktop açıldı.")),
    )
    type_and_send = MagicMock(return_value=(True, "ok"))
    monkeypatch.setattr(whatsapp, "_type_and_send", type_and_send)

    result = whatsapp.send_whatsapp_message(
        "Salam",
        phone_number="+994501234567",
        send_now=False,
        app_target="desktop",
    )

    assert "qaralama" in result
    type_and_send.assert_not_called()


def test_send_now_uses_automatic_send_path(monkeypatch):
    monkeypatch.setattr(whatsapp, "HAS_PYAUTOGUI", True)
    open_desktop = MagicMock(return_value=(True, "WhatsApp Desktop açıldı."))
    monkeypatch.setattr(whatsapp, "_open_whatsapp_desktop_via_scheme", open_desktop)
    type_and_send = MagicMock(return_value=(True, "ok"))
    monkeypatch.setattr(whatsapp, "_type_and_send", type_and_send)

    result = whatsapp.send_whatsapp_message(
        "Salam",
        phone_number="+994501234567",
        send_now=True,
        app_target="desktop",
    )

    assert "göndərildi" in result
    open_desktop.assert_called_once_with(
        "994501234567",
        "Salam",
        include_text=False,
    )
    type_and_send.assert_called_once_with("Salam", whatsapp.DESKTOP_LOAD_DELAY)


def test_tool_executor_dispatches_whatsapp_send():
    import asyncio
    from types import SimpleNamespace

    from core.tool_executor import ToolExecutor

    ui = MagicMock()
    ui.muted = False
    executor = ToolExecutor(ui, MagicMock(), MagicMock(), MagicMock())

    with patch(
        "core.tool_executor.send_whatsapp_message",
        return_value="WhatsApp Desktop içində qaralama mesaj açıldı.",
    ) as send:
        response = asyncio.run(
            executor.execute(
                SimpleNamespace(
                    id="wa-1",
                    name="send_whatsapp_message",
                    args={
                        "message": "Salam",
                        "phone_number": "+994501234567",
                        "send_now": False,
                        "app_target": "desktop",
                    },
                )
            )
        )

    send.assert_called_once_with(
        "Salam",
        "+994501234567",
        "",
        False,
        "desktop",
    )
    assert response.response["result"] == "WhatsApp Desktop içində qaralama mesaj açıldı."
