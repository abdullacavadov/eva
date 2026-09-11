"""EVA üçün səsli müdaxilə (barge-in) aşkarlama köməkçisi."""

from __future__ import annotations

import math
import struct
import time

from core.audio import get_microphone_speech_probability, interrupt_output_stream

try:
    from pywebrtc_audio import VoiceDetector
except Exception:
    VoiceDetector = None


class BargeInDetector:
    """Fon səslərini nitqdən ayıraraq yumşaq və tam müdaxiləni idarə edir."""

    def __init__(
        self,
        *,
        threshold: float = 0.045,
        confirm_ms: float = 260.0,
        sample_rate: int = 16000,
        speech_threshold: float = 0.35,
        confirm_speech_threshold: float = 0.55,
        candidate_hold_ms: float = 1000.0,
    ):
        self.threshold = max(0.0, float(threshold))
        self.confirm_ms = max(1.0, float(confirm_ms))
        self.sample_rate = max(1, int(sample_rate))
        self.speech_threshold = max(0.0, min(1.0, float(speech_threshold)))
        self.confirm_speech_threshold = max(
            self.speech_threshold,
            min(1.0, float(confirm_speech_threshold)),
        )
        self.candidate_hold_ms = max(0.0, float(candidate_hold_ms))
        self._active_ms = 0.0
        self._candidate_gap_ms = 0.0
        self._strong_seen = False
        self._confirmed = False
        self._speech_probability = 0.0
        self._detection_ready = False
        self._speech_candidate = False
        self._last_debug_log_at = 0.0
        self._voice_detector = VoiceDetector(
            sample_rate=self.sample_rate,
            num_channels=1,
        ) if VoiceDetector is not None else None

    @staticmethod
    def _raw_rms(data: bytes) -> float:
        if not data:
            return 0.0
        sample_count = len(data) // 2
        if sample_count <= 0:
            return 0.0
        samples = struct.unpack(f"<{sample_count}h", data[: sample_count * 2])
        mean_square = sum(sample * sample for sample in samples) / sample_count
        return math.sqrt(mean_square) / 32768.0

    def rms(self, data: bytes) -> float:
        """VAD namizədi olduqda mövcud ducking yoxlamasını aktiv saxlayır."""
        raw = self._raw_rms(data)
        if self._detection_ready:
            if not self._speech_candidate:
                return 0.0
            return max(raw, self.threshold)
        return raw

    def _detect_speech(
        self,
        data: bytes,
        speech_probability: float | None = None,
    ) -> tuple[bool, bool]:
        """Namizəd nitqi və güclü nitq siqnalını qaytarır."""
        if speech_probability is not None:
            self._speech_probability = max(0.0, min(1.0, float(speech_probability)))
            candidate = self._speech_probability >= self.speech_threshold
            strong_speech = self._speech_probability >= self.confirm_speech_threshold
            return candidate, strong_speech

        if not data or self._voice_detector is None:
            fallback = self._raw_rms(data) >= self.threshold
            return fallback, fallback

        try:
            import numpy as np

            samples = np.frombuffer(data, dtype=np.int16)
            if not len(samples):
                self._speech_probability = 0.0
                return False, False
            self._speech_probability = float(self._voice_detector.process(samples))
        except Exception:
            fallback = self._raw_rms(data) >= self.threshold
            self._speech_probability = 1.0 if fallback else 0.0
            return fallback, fallback

        candidate = self._speech_probability >= self.speech_threshold
        strong_speech = self._speech_probability >= self.confirm_speech_threshold
        return candidate, strong_speech

    @property
    def speech_probability(self) -> float:
        return self._speech_probability

    def is_speech_candidate(self) -> bool:
        """Cari state-ə görə nitq namizədinin aktiv olub-olmadığını qaytarır."""
        return self._speech_candidate

    def update(self, data: bytes) -> bool:
        """Chunk-u yoxlayır; təsdiqlənmiş nitq müdaxiləsində True qaytarır."""
        duration_ms = (len(data) / 2) / self.sample_rate * 1000.0
        speech_probability = get_microphone_speech_probability()
        candidate, strong_speech = self._detect_speech(
            data,
            speech_probability,
        )
        self._detection_ready = True

        now = time.monotonic()
        if now - self._last_debug_log_at >= 0.5:
            print(
                "[MIC-VAD] "
                f"chunk={len(data)}B "
                f"rms={self._raw_rms(data):.4f} "
                f"speech_probability={self._speech_probability:.3f} "
                f"candidate={candidate} "
                f"strong={strong_speech} "
                f"active_ms={self._active_ms:.0f} "
                f"speaking_candidate={self._speech_candidate}",
                flush=True,
            )
            self._last_debug_log_at = now

        if candidate:
            self._speech_candidate = True
            self._candidate_gap_ms = 0.0
            self._active_ms += duration_ms
            if strong_speech:
                self._strong_seen = True
        elif self._speech_candidate:
            self._candidate_gap_ms += duration_ms
            if self._candidate_gap_ms > self.candidate_hold_ms:
                self._speech_candidate = False
                self._candidate_gap_ms = 0.0
                self._active_ms = 0.0
                self._strong_seen = False
        else:
            self._active_ms = 0.0
            self._candidate_gap_ms = 0.0
            self._strong_seen = False

        if (
            not self._speech_candidate
            or self._active_ms < self.confirm_ms
            or not self._strong_seen
            or self._confirmed
        ):
            return False

        self._confirmed = True
        print(
            "[MIC-VAD] CONFIRMED — istifadəçi müdaxiləsi təsdiqləndi; playback interrupt edilir.",
            flush=True,
        )
        # Cari PyAudio write() əməliyyatını mümkün qədər dərhal kəsir.
        interrupt_output_stream()
        return True

    def reset(self) -> None:
        self._active_ms = 0.0
        self._candidate_gap_ms = 0.0
        self._strong_seen = False
        self._confirmed = False
        self._speech_probability = 0.0
        self._speech_candidate = False
        self._detection_ready = False
        self._last_debug_log_at = 0.0
        if self._voice_detector is not None:
            try:
                self._voice_detector.reset()
            except Exception:
                pass
