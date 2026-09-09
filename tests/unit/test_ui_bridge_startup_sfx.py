from queue import Queue

from core.ui_bridge import UiBridge


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def __iter__(self):
        return iter(())


class FakeSound:
    def __init__(self):
        self.played = 0

    def play_startup(self):
        self.played += 1


def make_bridge():
    bridge = UiBridge.__new__(UiBridge)
    bridge.ui = type("UI", (), {"sound": FakeSound()})()
    bridge._clients = set()
    bridge._client_queues = {}
    bridge._clients_lock = __import__("threading").Lock()
    bridge._last_state = None
    bridge._conversation_history = []
    bridge._activity_history = []
    bridge._last_context = None
    bridge._control_state = {}
    bridge._startup_sfx_played = False
    return bridge


def test_startup_sfx_plays_once_for_runtime_and_not_again_on_refresh():
    bridge = make_bridge()

    bridge._handle_client(FakeWebSocket())
    bridge._handle_client(FakeWebSocket())

    assert bridge.ui.sound.played == 1
