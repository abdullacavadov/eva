"""Phase 9 realtime audio configuration regression tests."""

from core.config import (
    CHUNK_SIZE,
    LIVE_INPUT_TRANSCRIPTION_LANGUAGE_CODES,
    SEND_SAMPLE_RATE,
)


def test_realtime_audio_chunk_is_low_latency():
    """16 kHz / 512-sample chunks keep microphone packets at 32 ms."""
    assert CHUNK_SIZE == 512
    assert CHUNK_SIZE / SEND_SAMPLE_RATE == 0.032


def test_azerbaijani_input_transcription_hint_is_enabled():
    assert "az-AZ" in LIVE_INPUT_TRANSCRIPTION_LANGUAGE_CODES
