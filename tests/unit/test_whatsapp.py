import actions.whatsapp as whatsapp

def test_send_whatsapp_message_reads_phone_number_field(monkeypatch):
    monkeypatch.setattr(
        whatsapp,
        "_contact_candidates",
        lambda: [
            {
                "display_name": "Miss Cavadova",
                "phone_number": "+994559041494",
                "aliases": ["Мисс Джавадова"],
                "_source": "whatsapp",
                "_key": "miss_cavadova",
            }
        ],
    )

    monkeypatch.setattr(
        whatsapp,
        "_open_whatsapp_desktop_via_scheme",
        lambda *args, **kwargs: (True, "ok"),
    )

    result = whatsapp.send_whatsapp_message(
        message="Salam",
        recipient_name="Мисс Джавадова",
        send_now=False,
        app_target="desktop",
    )

    assert "qaralama mesaj açıldı" in result


def test_send_now_replaces_existing_draft(monkeypatch):
    calls = []

    monkeypatch.setattr(
        whatsapp,
        "_open_whatsapp_desktop_via_scheme",
        lambda *args, **kwargs: (
            calls.append(("open", args, kwargs)) or (True, "ok")
        ),
    )

    monkeypatch.setattr(whatsapp, "HAS_PYAUTOGUI", True)

    monkeypatch.setattr(
        whatsapp,
        "_focus_whatsapp_window",
        lambda: calls.append(("focus",)),
    )

    class FakePyAutoGUI:
        @staticmethod
        def hotkey(*args):
            calls.append(("hotkey", *args))

        @staticmethod
        def press(*args):
            calls.append(("press", *args))

    monkeypatch.setattr(whatsapp, "pyautogui", FakePyAutoGUI)

    monkeypatch.setattr(
        whatsapp,
        "_copy_to_clipboard",
        lambda text: calls.append(("clipboard", text)),
    )

    monkeypatch.setattr(whatsapp.time, "sleep", lambda *_: None)

    result = whatsapp.send_whatsapp_message(
        message="Salam",
        phone_number="+994559041494",
        recipient_name="Miss Cavadova",
        send_now=True,
        app_target="desktop",
    )

    assert "mesaj göndərildi" in result
    assert ("hotkey", "ctrl", "a") in calls
    assert ("hotkey", "ctrl", "v") in calls
    assert ("press", "enter") in calls