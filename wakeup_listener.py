"""
İki dəfə əl çalma ilə wake tetikleyicisi.
"""

import math
import struct
import threading
import time
from typing import Callable

import pyaudio

SAMPLE_RATE = 16000
CHUNK = 1024
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
    """Ayrı dinləyici stream üzərindən iki ayrı əl çalmanı aşkarlayır."""

    def __init__(self, on_wake: Callable[[], None]):
        self._on_wake = on_wake
        self._running = False
        self._thread = None
        self._clap_times: list[float] = []
        self._last_clap = 0.0
        self._cooldown_until = 0.0
        self._noise_floor = 0.0
        self._above_threshold = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WakeClap")
        self._thread.start()

    def stop(self):
        self._running = False

    def process_chunk(self, data: bytes, now: float | None = None):
        """PCM chunk-u analiz edir və iki clap tamamlandıqda wake edir."""
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
        rising_edge = is_loud and not self._above_threshold
        self._above_threshold = is_loud

        self._clap_times = [
            t for t in self._clap_times if timestamp - t < CLAP_WINDOW
        ]

        if not rising_edge or timestamp < self._cooldown_until:
            return
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

    def _loop(self):
        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
            while self._running:
                data = stream.read(CHUNK, exception_on_overflow=False)
                self.process_chunk(data)
        except Exception as exc:
            print(f"[Wake] ❌ Alqış dinləyicisi xətası: {exc}")
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()
