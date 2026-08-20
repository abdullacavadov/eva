from dataclasses import dataclass

from actions.whatsapp_read import read_visible_whatsapp_messages


@dataclass
class Message:
    message_id: str
    conversation_id: str
    sender: str = ""
    sender_phone: str = ""
    content: str = ""
    timestamp: str = ""
    direction: str = "incoming"


class Bridge:
    def __init__(self, messages):
        self.messages = messages

    def get_visible_messages(self):
        return self.messages


def test_visible_messages_are_converted_to_structured_result(tmp_path):
    bridge = Bridge([
        Message(
            message_id="m1",
            conversation_id="c1",
            sender="Ali",
            content="Salam",
            timestamp="2026-08-20T12:00:00",
        )
    ])

    result = read_visible_whatsapp_messages(
        bridge,
        seen_path=tmp_path / "seen.json",
    )

    assert result["type"] == "whatsapp_message"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["message_id"] == "m1"
    assert result["data"][0]["conversation_id"] == "c1"


def test_seen_messages_are_deduplicated(tmp_path):
    path = tmp_path / "seen.json"
    bridge = Bridge([
        Message(message_id="m1", conversation_id="c1", content="Salam"),
        Message(message_id="m2", conversation_id="c1", content="Necəsən?"),
    ])

    first = read_visible_whatsapp_messages(bridge, seen_path=path)
    second = read_visible_whatsapp_messages(bridge, seen_path=path)

    assert first["count"] == 2
    assert second["status"] == "empty"
    assert second["count"] == 0


def test_duplicate_message_ids_in_same_poll_are_deduplicated(tmp_path):
    bridge = Bridge([
        Message(message_id="m1", conversation_id="c1", content="Salam"),
        Message(message_id="m1", conversation_id="c1", content="Salam"),
    ])

    result = read_visible_whatsapp_messages(
        bridge,
        seen_path=tmp_path / "seen.json",
    )

    assert result["count"] == 1
    assert result["data"][0]["message_id"] == "m1"
