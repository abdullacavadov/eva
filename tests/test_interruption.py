import struct

from core import interruption
from core.interruption import BargeInDetector


class FakeVoiceDetector:
    def __init__(self, sample_rate, num_channels):
        self.probabilities = []

    def process(self, samples):
        return self.probabilities.pop(0)

    def reset(self):
        self.probabilities.clear()


def pcm_chunk(value: int = 10000, samples: int = 512) -> bytes:
    return struct.pack(f"<{samples}h", *([value] * samples))


def test_short_speech_candidate_ducks_and_restores(monkeypatch):
    monkeypatch.setattr(interruption, "VoiceDetector", FakeVoiceDetector)
    detector = BargeInDetector(sample_rate=16000, candidate_hold_ms=120.0)
    detector._voice_detector.probabilities = [0.40] + [0.10] * 8

    assert detector.update(pcm_chunk()) is False
    assert detector.is_speech_candidate() is True
    assert detector.rms(pcm_chunk()) > detector.threshold

    assert detector.update(pcm_chunk()) is False
    assert detector.is_speech_candidate() is True
    assert detector.rms(pcm_chunk()) > detector.threshold

    assert detector.update(pcm_chunk()) is False
    assert detector.is_speech_candidate() is True

    # 3 x 32 ms = 96 ms səssizlikdə namizəd hələ aktiv qalır.
    assert detector.update(pcm_chunk()) is False
    assert detector.is_speech_candidate() is True

    # Növbəti 32 ms ilə ümumi boşluq 128 ms olur və 120 ms həddini keçir.
    assert detector.update(pcm_chunk()) is False
    assert detector.is_speech_candidate() is False
    assert detector.rms(pcm_chunk()) == 0.0


def test_speech_candidate_survives_short_vad_gap(monkeypatch):
    monkeypatch.setattr(interruption, "VoiceDetector", FakeVoiceDetector)
    detector = BargeInDetector(
        sample_rate=16000,
        confirm_ms=260.0,
        candidate_hold_ms=120.0,
    )
    detector._voice_detector.probabilities = [0.80, 0.80, 0.10] + [0.80] * 15

    assert detector.update(pcm_chunk()) is False
    assert detector.update(pcm_chunk()) is False
    assert detector.update(pcm_chunk()) is False
    assert detector.is_speech_candidate() is True

    confirmed = False
    for _ in range(15):
        confirmed = detector.update(pcm_chunk()) or confirmed

    assert confirmed is True


def test_confirmed_speech_interrupts_after_confirmation(monkeypatch):
    monkeypatch.setattr(interruption, "VoiceDetector", FakeVoiceDetector)
    interrupt_calls = []
    monkeypatch.setattr(
        interruption,
        "interrupt_output_stream",
        lambda: interrupt_calls.append(True),
    )

    detector = BargeInDetector(sample_rate=16000, confirm_ms=260.0)
    detector._voice_detector.probabilities = [0.80] * 9

    confirmed = False
    for _ in range(9):
        confirmed = detector.update(pcm_chunk()) or confirmed

    assert confirmed is True
    assert interrupt_calls == [True]
    assert detector.is_speech_candidate() is True
