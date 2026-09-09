"""EVA üçün səsli müdaxilə (barge-in) aşkarlama köməkçisi."""

from __future__ import annotations

import math
import struct

from core.audio import interrupt_output_stream


class BargeInDetector:
    """Qısa fon səslərini filtr edib davamlı insan nitqini aşkarlayır."""

    def __init__(self, *, threshold: float = 0.045, confirm_ms: float = 260.0, sample_rate: int = 16000):
        self.threshold = max(0.0, float(threshold))
        self.confirm_ms = max(1.0, float(confirm_ms))
        self.sample_rate = max(1, int(sample_rate))
        self._active_ms = 0.0
        self._confirmed = False

    @staticmethod
    def rms(data: bytes) -> float:
        if not data:
            return 0.0
        sample_count = len(data) // 2
        if sample_count <= 0:
            return 0.0
        samples = struct.unpack(f"<{sample_count}h", data[: sample_count * 2])
        mean_square = sum(sample * sample for sample in samples) / sample_count
        return math.sqrt(mean_square) / 32768.0

    def update(self, data: bytes) -> bool:
        """Chunk-u yoxlayır; təsdiqlənmiş müdaxilə olduqda True qaytarır."""
        duration_ms = (len(data) / 2) / self.sample_rate * 1000.0
        if self.rms(data) >= self.threshold:
            self._active_ms += duration_ms
        else:
            self._active_ms = 0.0

        if self._active_ms < self.confirm_ms or self._confirmed:
            return False

        self._confirmed = True
        # Cari PyAudio write() əməliyyatını mümkün qədər dərhal kəsir.
        interrupt_output_stream()
        return True

    def reset(self) -> None:
        self._active_ms = 0.0
        self._confirmed = False
