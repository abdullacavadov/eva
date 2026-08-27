import json

from core.ui_bridge import UiBridge


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(json.loads(message))


def make_bridge(callback):
    bridge = UiBridge.__new__(UiBridge)
    bridge.ui = type("UI", (), {"on_control_command": callback})()
    bridge._control_state = {
        "paused": False,
        "camera_active": False,
        "microphone_muted": False,
    }
    bridge.emit = lambda event_type, **payload: None
    return bridge


def test_control_command_updates_state():
    bridge = make_bridge(lambda command: {"paused": command == "pause"})
    websocket = FakeWebSocket()

    bridge._handle_message(websocket, json.dumps({"type": "control.command", "command": "pause"}))

    assert bridge._control_state["paused"] is True
    assert websocket.sent == []


def test_unknown_control_command_returns_error():
    bridge = make_bridge(lambda command: {})
    websocket = FakeWebSocket()

    bridge._handle_message(websocket, json.dumps({"type": "control.command", "command": "invalid"}))

    assert websocket.sent == [
        {"type": "bridge.error", "message": "Naməlum idarəetmə əmri."}
    ]


def test_control_command_requires_runtime_callback():
    bridge = UiBridge.__new__(UiBridge)
    bridge.ui = type("UI", (), {})()
    bridge._control_state = {}
    bridge.emit = lambda event_type, **payload: None
    websocket = FakeWebSocket()

    bridge._handle_message(websocket, json.dumps({"type": "control.command", "command": "camera"}))

    assert websocket.sent == [
        {"type": "bridge.error", "message": "EVA control callback-i hazır deyil."}
    ]
