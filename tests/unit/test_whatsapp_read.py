from pathlib import Path

from actions.whatsapp_read import read_visible_whatsapp_conversations, read_visible_whatsapp_messages
from integrations.whatsapp.web import WhatsAppVisibleConversation, WhatsAppVisibleMessage


class FakeBridge:
    def __init__(self, messages=None, conversations=None):
        self.messages = messages or []
        self.conversations = conversations or []

    def get_visible_messages(self):
        return self.messages

    def get_visible_conversations(self):
        return self.conversations


def _message(message_id, content="Salam"):
    return WhatsAppVisibleMessage(
        message_id=message_id,
        conversation_id="conversation-1",
        sender="Ali",
        sender_phone="+994500000000",
        content=content,
        timestamp="12:00",
        direction="incoming",
    )


def _conversation(title, unread_count=0):
    return WhatsAppVisibleConversation(
        conversation_id=title,
        title=title,
        contact_name=title,
        contact_phone="",
        last_message="",
        last_message_timestamp="",
        unread_count=unread_count,
    )


def test_visible_messages_are_deduplicated(tmp_path: Path):
    bridge = FakeBridge(messages=[_message("m1"), _message("m1"), _message("m2")])

    result = read_visible_whatsapp_messages(bridge, tmp_path / "seen.json")

    assert result["type"] == "whatsapp_message"
    assert result["count"] == 2
    assert [item["message_id"] for item in result["data"]] == ["m1", "m2"]


def test_seen_messages_are_skipped_on_subsequent_reads(tmp_path: Path):
    seen_path = tmp_path / "seen.json"
    bridge = FakeBridge(messages=[_message("m1")])

    first = read_visible_whatsapp_messages(bridge, seen_path)
    second = read_visible_whatsapp_messages(bridge, seen_path)

    assert first["count"] == 1
    assert second["status"] == "empty"
    assert second["count"] == 0


def test_message_result_contains_structured_fields(tmp_path: Path):
    result = read_visible_whatsapp_messages(
        FakeBridge(messages=[_message("m1", "Test mesaj")]),
        tmp_path / "seen.json",
    )

    item = result["data"][0]
    assert item["id"] == "whatsapp:message:m1"
    assert item["conversation_id"] == "conversation-1"
    assert item["sender"] == "Ali"
    assert item["content"] == "Test mesaj"
    assert item["direction"] == "incoming"


def test_visible_conversations_preserve_unread_counts():
    bridge = FakeBridge(
        conversations=[
            _conversation("Мис Джавадова", 4),
            _conversation("Махмуд", 1),
            _conversation("Рашад Гурбанлы", 0),
        ]
    )

    result = read_visible_whatsapp_conversations(bridge)

    assert result["type"] == "whatsapp_conversation"
    assert result["count"] == 3
    assert [
        (item["title"], item["unread_count"])
        for item in result["data"]
    ] == [
        ("Мис Джавадова", 4),
        ("Махмуд", 1),
        ("Рашад Гурбанлы", 0),
    ]


def test_conversation_result_defaults_unread_count_to_zero():
    bridge = FakeBridge(conversations=[_conversation("Рашад Гурбанлы")])

    result = read_visible_whatsapp_conversations(bridge)

    assert result["data"][0]["unread_count"] == 0
