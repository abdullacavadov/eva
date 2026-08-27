import asyncio

import pytest

from core.live_session import LiveSessionManager, _ResilientLiveSession


@pytest.mark.asyncio
async def test_reconnect_calls_share_one_task(monkeypatch):
    manager = LiveSessionManager("test-model", "test-key")
    session = _ResilientLiveSession(manager, config={})
    calls = 0

    async def fake_reconnect_impl(*, force_fresh=False):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)

    monkeypatch.setattr(session, "_reconnect_impl", fake_reconnect_impl)

    await asyncio.gather(session._reconnect(), session._reconnect())

    assert calls == 1


@pytest.mark.asyncio
async def test_receive_uses_low_level_receive_across_multiple_turns():
    manager = LiveSessionManager("test-model", "test-key")
    session = _ResilientLiveSession(manager, config={})

    class FakeLiveSession:
        def __init__(self):
            self.calls = 0

        async def _receive(self):
            self.calls += 1
            return object()

    fake = FakeLiveSession()
    session._session = fake
    messages = session.receive()

    await messages.__anext__()
    await messages.__anext__()
    await messages.aclose()

    assert fake.calls == 2


class _CleanCloseError(Exception):
    code = 1000


def test_clean_websocket_close_is_detected():
    assert _ResilientLiveSession._is_clean_close(_CleanCloseError()) is True
    assert _ResilientLiveSession._is_clean_close(RuntimeError("boom")) is False
