import asyncio

from core.config import (
    LIVE_INPUT_TRANSCRIPTION_LANGUAGE_CODES,
    LIVE_INPUT_TRANSCRIPTION_MODE,
    LIVE_THINKING_LEVEL,
)
from core.live_session import LiveSessionManager, _ResilientLiveSession


def test_reconnect_calls_share_one_task(monkeypatch):
    manager = LiveSessionManager("test-model", "test-key")
    session = _ResilientLiveSession(manager, config={})
    calls = 0

    async def fake_reconnect_impl(*, force_fresh=False):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)

    monkeypatch.setattr(session, "_reconnect_impl", fake_reconnect_impl)

    async def run():
        await asyncio.gather(session._reconnect(), session._reconnect())

    asyncio.run(run())

    assert calls == 1


def test_receive_uses_low_level_receive_across_multiple_turns():
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

    async def run():
        messages = session.receive()
        await messages.__anext__()
        await messages.__anext__()
        await messages.aclose()

    asyncio.run(run())

    assert fake.calls == 2


class _CleanCloseError(Exception):
    code = 1000


def test_clean_websocket_close_is_detected():
    assert _ResilientLiveSession._is_clean_close(_CleanCloseError()) is True
    assert _ResilientLiveSession._is_clean_close(RuntimeError("boom")) is False


def test_live_connect_config_defaults_to_multilingual_smart_transcription():
    from google.genai import types

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription={},
    )

    assert config.input_audio_transcription.language_codes == LIVE_INPUT_TRANSCRIPTION_LANGUAGE_CODES
    assert config.input_audio_transcription.mode == LIVE_INPUT_TRANSCRIPTION_MODE


def test_live_connect_config_defaults_to_minimal_thinking():
    from google.genai import types

    config = types.LiveConnectConfig(response_modalities=["AUDIO"])

    assert config.thinking_config.thinking_level.value.lower() == LIVE_THINKING_LEVEL


def test_context_token_estimate_is_four_characters_per_token():
    from core.config import _estimate_tokens

    assert _estimate_tokens("") == 0
    assert _estimate_tokens("1234") == 1
    assert _estimate_tokens("12345678") == 2
    assert _estimate_tokens("123") == 1


def test_session_config_includes_stored_resume_handle():
    manager = LiveSessionManager("test-model", "test-key")
    manager.resume_handle = "resume-123"
    session = _ResilientLiveSession(manager, config={})

    config = session._session_config

    assert config["session_resumption"].handle == "resume-123"


def test_resume_handle_update_persists_in_manager():
    manager = LiveSessionManager("test-model", "test-key")

    class Update:
        resumable = True
        new_handle = "resume-123"

    class Message:
        session_resumption_update = Update()

    current = _ResilientLiveSession._update_resume_handle(manager, None, Message())

    assert current == "resume-123"
    assert manager.resume_handle == "resume-123"


def test_force_fresh_reconnect_clears_resume_handle(monkeypatch):
    manager = LiveSessionManager("test-model", "test-key")
    manager.resume_handle = "resume-123"
    session = _ResilientLiveSession(manager, config={})
    session._resume_handle = "resume-123"

    async def fake_sleep(_delay):
        return None

    async def fake_close_current():
        return None

    async def fake_connect(*, clear_handle_on_failure=False):
        session._closed = True

    monkeypatch.setattr("core.live_session.asyncio.sleep", fake_sleep)
    monkeypatch.setattr(session, "_close_current", fake_close_current)
    monkeypatch.setattr(session, "_connect", fake_connect)

    async def run():
        await session._reconnect_impl(force_fresh=True)

    asyncio.run(run())

    assert session._resume_handle is None
    assert manager.resume_handle is None
