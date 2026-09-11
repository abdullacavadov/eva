import asyncio
import struct

import numpy as np

import core.audio as audio


def test_aec_default_delay_matches_playback_buffer(monkeypatch):
    captured = {}

    class FakeAudioProcessor:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.delenv("EVA_AEC_DELAY_MS", raising=False)
    monkeypatch.setattr(audio, "AudioProcessor", FakeAudioProcessor)

    processor = audio._RealtimeEchoCanceller()

    assert processor._delay_ms == 20
    assert captured["stream_delay_ms"] == 20


def test_aec_delay_can_be_overridden(monkeypatch):
    captured = {}

    class FakeAudioProcessor:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("EVA_AEC_DELAY_MS", "35")
    monkeypatch.setattr(audio, "AudioProcessor", FakeAudioProcessor)

    processor = audio._RealtimeEchoCanceller()

    assert processor._delay_ms == 35
    assert captured["stream_delay_ms"] == 35


def test_aec_reference_resamples_playback_to_microphone_rate():
    samples = np.arange(480, dtype=np.int16)
    data = samples.tobytes()

    reference = audio._RealtimeEchoCanceller._resample(data)

    assert len(reference) == 320
    assert reference.dtype == np.int16


def test_read_chunk_returns_echo_cancelled_audio(monkeypatch):
    expected = struct.pack("<4h", 1, 2, 3, 4)

    class FakeEchoCanceller:
        def process_microphone(self, data):
            assert data == b"raw"
            return expected

    monkeypatch.setattr(audio, "_echo_canceller", FakeEchoCanceller())

    class FakeStream:
        def read(self, size, exception_on_overflow=False):
            assert size == 4
            assert exception_on_overflow is False
            return b"raw"

    result = asyncio.run(audio.read_chunk(FakeStream(), 4))

    assert result == expected


def test_write_chunk_registers_the_same_playback_signal_used_by_output(monkeypatch):
    references = []

    class FakeEchoCanceller:
        def add_playback_reference(self, data):
            references.append(data)

    monkeypatch.setattr(audio, "_echo_canceller", FakeEchoCanceller())

    class FakeStream:
        def write(self, data, exception_on_underflow=False):
            assert exception_on_underflow is False
            assert data == struct.pack("<4h", 500, -500, 1000, -1000)

    asyncio.run(audio.write_chunk(FakeStream(), struct.pack("<4h", 1000, -1000, 2000, -2000), gain=0.5))

    assert references == [struct.pack("<4h", 500, -500, 1000, -1000)]
