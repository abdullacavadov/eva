"""
İki dəfə əl çalma ilə wake tetikleyicisi.

Detector əsas mikrofon axınından PCM chunk qəbul edir. Ayrı PyAudio input
stream açmır; beləliklə EVA-nın əsas mikrofon axını ilə konflikt yaratmır.
"""

import math
import struct
import time
from typing import Callable

CLAP_WINDOW = 2.0
CLAP_MIN_GAP = 0.18
CLAP_COOLDOWN = 1.0
NOISE_FLOOR_ALPHA = 0.05
THRESHOLD_MULTIPLIER = 3.0
MIN_THRESHOLD = 1200.0
MAX_THRESHOLD = 7000.0


def _rms(data: bytes) -> float:
    count = len(data) // 2
    if count <= 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", data[:count * 2])
    return math.sqrt(sum(sample * sample for sample in samples) / count)


class WakeGestureListener:
    """Əsas mikrofon PCM axınından iki ayrı əl çalmanı aşkarlayır."""

    def __init__(self, on_wake: Callable[[], None]):
        self._on_wake = on_wake
        self._running = False
        self._clap_times: list[float] = []
        self._last_clap = 0.0
        self._cooldown_until = 0.0
        self._noise_floor = 0.0
        self._above_threshold = False

    def start(self):
        # Uyğunluq üçün saxlanılır. Detector ayrıca thread/stream açmır.
        self._running = True

    def stop(self):
        self._running = False
        self._clap_times.clear()
        self._above_threshold = False

    def process_chunk(self, data: bytes, now: float | None = None):
        """Əsas mikrofon axınından gələn PCM chunk-u emal edir."""
        if not self._running or not data:
            return

        timestamp = time.monotonic() if now is None else now
        rms = _rms(data)

        if self._noise_floor <= 0.0:
            self._noise_floor = rms
        else:
            self._noise_floor = (
                self._noise_floor * (1.0 - NOISE_FLOOR_ALPHA)
                + rms * NOISE_FLOOR_ALPHA
            )

        threshold = min(
            MAX_THRESHOLD,
            max(MIN_THRESHOLD, self._noise_floor * THRESHOLD_MULTIPLIER),
        )
        is_loud = rms >= threshold

        # Bir clap bir neçə audio chunk-a yayıla bilər. Yalnız səssizdən
        # yüksək impuls səviyyəsinə keçidi ayrıca clap kimi qəbul et.
        rising_edge = is_loud and not self._above_threshold
        self._above_threshold = is_loud
        if not rising_edge or timestamp < self._cooldown_until:
            self._clap_times = [t for t in self._clap_times if timestamp - t < CLAP_WINDOW]
            return

        self._clap_times = [t for t in self._clap_times if timestamp - t < CLAP_WINDOW]
        if self._last_clap and timestamp - self._last_clap < CLAP_MIN_GAP:
            return

        self._last_clap = timestamp
        self._clap_times.append(timestamp)
        print(f"[Wake] 👏 Alqış #{len(self._clap_times)}")

        if len(self._clap_times) >= 2:
            self._clap_times.clear()
            self._cooldown_until = timestamp + CLAP_COOLDOWN
            print("[Wake] ✅ Cüt alqışla ekran açılır")
            try:
                self._on_wake()
            except Exception as exc:
                print(f"[Wake] ❌ Wake callback xətası: {exc}")
