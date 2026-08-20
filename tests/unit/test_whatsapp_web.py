from integrations.whatsapp.web import WhatsAppWebBridge


class FakeLocator:
    def __init__(self, text="", count=0):
        self._text = text
        self._count = count
        self.first = self

    def count(self):
        return self._count

    def inner_text(self):
        return self._text


class FakeMessage:
    def __init__(self, data_id="", content="", author="", meta="", outgoing=False):
        self._data_id = data_id
        self._fields = {
            '[data-testid="selectable-text"]': content,
            '[data-testid="author"]': author,
            '[data-testid="msg-meta"]': meta,
        }
        self._outgoing = outgoing

    def get_attribute(self, name):
        if name == "data-id":
            return self._data_id
        return None

    def locator(self, selector):
        if selector == '[data-testid="msg-outgoing"]':
            return FakeLocator(count=1 if self._outgoing else 0)
        value = self._fields.get(selector, "")
        return FakeLocator(text=value, count=1 if value else 0)


class FakePage:
    def __init__(self, messages, conversation_id="Test conversation"):
        self._messages = messages
        self._conversation_id = conversation_id

    def locator(self, selector):
        if selector == '[data-testid="msg-container"]':
            return FakeLocatorList(self._messages)
        if selector == '[data-testid="conversation-header"]':
            return FakeLocator(text=self._conversation_id, count=1)
        return FakeLocator()


class FakeLocatorList:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


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


def test_get_visible_messages_parses_message_nodes_without_msg_time():
    bridge = WhatsAppWebBridge(".whatsapp-test-profile")
    bridge._page = FakePage(
        [
            FakeMessage(
                data_id="true-id",
                content="hello",
                author="Alice",
                meta="10:15",
            ),
            FakeMessage(
                content="",
                author="Bob",
                meta="10:16",
                outgoing=True,
            ),
        ]
    )

    messages = bridge.get_visible_messages()

    assert len(messages) == 2
    assert messages[0].message_id == "true-id"
    assert messages[0].sender == "Alice"
    assert messages[0].content == "hello"
    assert messages[0].timestamp == "10:15"
    assert messages[0].direction == "incoming"
    assert messages[1].sender == "Bob"
    assert messages[1].content == ""
    assert messages[1].timestamp == "10:16"
    assert messages[1].direction == "outgoing"
    assert messages[1].message_id == "Test conversation:dom-1:Bob:10:16:outgoing"
