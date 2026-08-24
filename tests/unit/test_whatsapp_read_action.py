from actions.whatsapp_read_action import read_whatsapp_conversations, read_whatsapp_messages
from integrations.whatsapp.web import WhatsAppVisibleConversation, WhatsAppVisibleMessage


class FakeBridge:
    def __init__(self, user_data_dir):
        self.user_data_dir = user_data_dir

    def connect(self):
        pass

    def close(self):
        pass

    def _require_page(self):
        return self

    def locator(self, selector):
        return self

    def filter(self, **kwargs):
        return self

    @property
    def first(self):
        return self

    def click(self):
        pass

    def wait_for_timeout(self, _ms):
        pass

    def get_visible_conversations(self):
        return [
            WhatsAppVisibleConversation(
                conversation_id="c1",
                title="Ali",
                contact_name="Ali",
                contact_phone="+994500000000",
                last_message="",
                last_message_timestamp="",
            )
        ]

    def get_visible_messages(self):
        return [
            WhatsAppVisibleMessage(
                message_id="m1",
                conversation_id="c1",
                sender="Ali",
                sender_phone="+994500000000",
                content="Salam",
                timestamp="12:00",
                direction="incoming",
            )
        ]


def test_read_whatsapp_conversations_uses_structured_contract(monkeypatch):
    monkeypatch.setattr("actions.whatsapp_read_action.WhatsAppWebBridge", FakeBridge)

    result = read_whatsapp_conversations()

    assert result["type"] == "whatsapp_conversation"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["conversation_id"] == "c1"


def test_read_whatsapp_messages_uses_existing_message_contract(monkeypatch, tmp_path):
    monkeypatch.setattr("actions.whatsapp_read_action.WhatsAppWebBridge", FakeBridge)
    monkeypatch.setenv("EVA_WHATSAPP_SEEN_FILE", str(tmp_path / "seen.json"))

    result = read_whatsapp_messages()

    assert result["type"] == "whatsapp_message"
    assert result["status"] == "success"
    assert result["count"] == 1
    item = result["data"][0]
    assert item["id"] == "whatsapp:message:m1"
    assert item["conversation_id"] == "c1"
    assert item["sender"] == "Ali"
    assert item["timestamp"] == "12:00"
    assert item["direction"] == "incoming"
    assert item["content"] == "Salam"


def test_read_whatsapp_messages_rejects_ambiguous_partial_match(monkeypatch, tmp_path):
    class AmbiguousBridge(FakeBridge):
        def get_visible_conversations(self):
            return [
                WhatsAppVisibleConversation(
                    conversation_id="c1",
                    title="Ali Baba",
                    contact_name="Ali Baba",
                    contact_phone="",
                    last_message="",
                    last_message_timestamp="",
                    unread_count=2,
                ),
                WhatsAppVisibleConversation(
                    conversation_id="c2",
                    title="Ali Veli",
                    contact_name="Ali Veli",
                    contact_phone="",
                    last_message="",
                    last_message_timestamp="",
                    unread_count=1,
                ),
            ]

    monkeypatch.setattr("actions.whatsapp_read_action.WhatsAppWebBridge", AmbiguousBridge)
    monkeypatch.setenv("EVA_WHATSAPP_SEEN_FILE", str(tmp_path / "seen.json"))

    result = read_whatsapp_messages("Ali")

    assert result["type"] == "whatsapp_message"
    assert result["status"] == "error"
    assert result["count"] == 2
    assert result["selected"] is None
    assert result["meta"]["ambiguous"] is True
    assert result["meta"]["candidates"] == ["Ali Baba", "Ali Veli"]
    assert [item["title"] for item in result["data"]] == ["Ali Baba", "Ali Veli"]


def test_read_whatsapp_messages_keeps_exact_match_precedence(monkeypatch, tmp_path):
    class ExactBridge(FakeBridge):
        def get_visible_conversations(self):
            return [
                WhatsAppVisibleConversation(
                    conversation_id="c1",
                    title="Ali",
                    contact_name="Ali",
                    contact_phone="",
                    last_message="",
                    last_message_timestamp="",
                ),
                WhatsAppVisibleConversation(
                    conversation_id="c2",
                    title="Ali Baba",
                    contact_name="Ali Baba",
                    contact_phone="",
                    last_message="",
                    last_message_timestamp="",
                ),
            ]

    monkeypatch.setattr("actions.whatsapp_read_action.WhatsAppWebBridge", ExactBridge)
    monkeypatch.setenv("EVA_WHATSAPP_SEEN_FILE", str(tmp_path / "seen.json"))

    result = read_whatsapp_messages("Ali")

    assert result["status"] == "success"
    assert result["data"][0]["conversation_id"] == "c1"
