import asyncio
import struct

import numpy as np

import core.audio as audio


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
