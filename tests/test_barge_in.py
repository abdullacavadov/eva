import struct

from core.audio import apply_gain
from core import interruption
from core.interruption import BargeInDetector


def _pcm(value: int, samples: int = 1600) -> bytes:
    return struct.pack(f"<{samples}h", *([value] * samples))


def _detector_with_vad(monkeypatch, probabilities, **kwargs):
    class FakeVoiceDetector:
        def __init__(self, sample_rate, num_channels):
            self.probabilities = list(probabilities)

        def process(self, samples):
            return self.probabilities.pop(0)

        def reset(self):
            self.probabilities.clear()

    monkeypatch.setattr(interruption, "VoiceDetector", FakeVoiceDetector)
    return BargeInDetector(**kwargs)


def test_barge_in_ignores_short_noise(monkeypatch):
    detector = _detector_with_vad(
        monkeypatch,
        [0.10, 0.10],
        threshold=0.04,
        confirm_ms=260,
        sample_rate=16000,
    )

    assert detector.update(_pcm(1800, 1600)) is False  # 100 ms
    assert detector.update(_pcm(0, 1600)) is False


def test_barge_in_confirms_continuous_speech(monkeypatch):
    detector = _detector_with_vad(
        monkeypatch,
        [0.80, 0.80, 0.80],
        threshold=0.04,
        confirm_ms=250,
        sample_rate=16000,
    )
    chunk = _pcm(2500, 1600)  # 100 ms

    assert detector.update(chunk) is False
    assert detector.update(chunk) is False
    assert detector.update(chunk) is True


def test_barge_in_aborts_playback_once(monkeypatch):
    calls = []
    monkeypatch.setattr("core.interruption.interrupt_output_stream", lambda: calls.append(True) or True)
    detector = _detector_with_vad(
        monkeypatch,
        [0.80, 0.80, 0.80, 0.80],
        threshold=0.04,
        confirm_ms=250,
        sample_rate=16000,
    )
    chunk = _pcm(2500, 1600)

    detector.update(chunk)
    detector.update(chunk)
    assert detector.update(chunk) is True
    assert detector.update(chunk) is False
    assert calls == [True]


def test_barge_in_reset_clears_accumulated_speech(monkeypatch):
    detector = _detector_with_vad(
        monkeypatch,
        [0.80, 0.80, 0.80],
        threshold=0.04,
        confirm_ms=250,
        sample_rate=16000,
    )
    chunk = _pcm(2500, 1600)

    detector.update(chunk)
    detector.reset()

    assert detector.update(chunk) is False


def test_apply_gain_reduces_pcm_amplitude():
    source = _pcm(12000, 4)

    ducked = apply_gain(source, 0.25)

    assert struct.unpack("<4h", ducked) == (3000, 3000, 3000, 3000)


def test_apply_gain_keeps_full_volume_unchanged():
    source = _pcm(-12000, 4)

    assert apply_gain(source, 1.0) == source
