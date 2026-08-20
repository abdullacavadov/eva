from integrations.whatsapp.web import WhatsAppWebBridge


def test_bridge_does_not_expose_send_operation():
    assert not hasattr(WhatsAppWebBridge, "send_message")
    assert not hasattr(WhatsAppWebBridge, "send")


def test_bridge_requires_connection_before_reading():
    bridge = WhatsAppWebBridge(".whatsapp-test-profile")

    try:
        bridge.get_visible_messages()
        assert False, "Expected read operation to require an active connection"
    except RuntimeError as exc:
        assert "qoşulmayıb" in str(exc)
