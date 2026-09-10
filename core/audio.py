import asyncio
import os
import struct
import threading
import time
from collections import deque

import numpy as np
import pyaudio

from core.config import CHUNK_SIZE, PLAYBACK_CHUNK_SIZE

try:
    from pywebrtc_audio import AudioProcessor
except Exception:
    AudioProcessor = None

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000


class _RealtimeEchoCanceller:
    def __init__(self):
        self._lock = threading.Lock()
        self._processor = None
        self._far_segments = deque()
        self._delay_ms = max(0, int(os.getenv("EVA_AEC_DELAY_MS", "0")))
        self._max_reference_seconds = 2.0
        self._playback_cursor = None
        self._playback_gap_reset_seconds = 0.1
        if AudioProcessor is not None:
            try:
                self._processor = AudioProcessor(
                    sample_rate=SEND_SAMPLE_RATE,
                    num_channels=CHANNELS,
                    echo_cancellation=True,
                    noise_suppression=True,
                    auto_gain_control=False,
                    stream_delay_ms=self._delay_ms,
                )
            except Exception as exc:
                print(f"[E.V.A] ⚠️ AEC aktivləşdirilə bilmədi: {exc}", flush=True)

    @property
    def enabled(self) -> bool:
        return self._processor is not None

    @staticmethod
    def _resample(data: bytes) -> np.ndarray:
        if len(data) % 2:
            return np.zeros(0, dtype=np.int16)
        samples = np.frombuffer(data, dtype=np.int16)
        if not len(samples):
            return np.zeros(0, dtype=np.int16)
        if RECV_SAMPLE_RATE == SEND_SAMPLE_RATE:
            return samples.copy()
        target_size = round(len(samples) * SEND_SAMPLE_RATE / RECV_SAMPLE_RATE)
        if target_size <= 0:
            return np.zeros(0, dtype=np.int16)
        positions = np.linspace(0, len(samples) - 1, target_size)
        return np.interp(positions, np.arange(len(samples)), samples).astype(np.int16)

    def add_playback_reference(self, data: bytes):
        if not self.enabled or not data or len(data) % 2:
            return
        reference = self._resample(data)
        if not len(reference):
            return

        now = time.monotonic()
        duration = len(reference) / SEND_SAMPLE_RATE

        with self._lock:
            if self._playback_cursor is None:
                start_time = now + self._delay_ms / 1000.0
            else:
                gap = now - self._playback_cursor
                if gap > self._playback_gap_reset_seconds:
                    start_time = now + self._delay_ms / 1000.0
                else:
                    start_time = self._playback_cursor

            self._far_segments.append((start_time, reference))
            self._playback_cursor = start_time + duration
            self._trim_reference(self._playback_cursor)

    def _trim_reference(self, current_time: float):
        cutoff = current_time - self._max_reference_seconds
        while self._far_segments:
            start_time, samples = self._far_segments[0]
            end_time = start_time + len(samples) / SEND_SAMPLE_RATE
            if end_time > cutoff:
                break
            self._far_segments.popleft()

    def _reference_for_interval(self, start_time: float, end_time: float) -> np.ndarray:
        length = max(0, round((end_time - start_time) * SEND_SAMPLE_RATE))
        far = np.zeros(length, dtype=np.int16)
        if length == 0:
            return far

        for segment_start, samples in self._far_segments:
            segment_end = segment_start + len(samples) / SEND_SAMPLE_RATE
            if segment_end <= start_time:
                continue
            if segment_start >= end_time:
                break

            overlap_start = max(start_time, segment_start)
            overlap_end = min(end_time, segment_end)
            if overlap_end <= overlap_start:
                continue

            destination_start = round((overlap_start - start_time) * SEND_SAMPLE_RATE)
            destination_end = round((overlap_end - start_time) * SEND_SAMPLE_RATE)
            source_start = round((overlap_start - segment_start) * SEND_SAMPLE_RATE)
            source_end = source_start + (destination_end - destination_start)

            destination_start = max(0, min(length, destination_start))
            destination_end = max(destination_start, min(length, destination_end))
            source_start = max(0, min(len(samples), source_start))
            source_end = max(source_start, min(len(samples), source_end))

            copy_length = min(
                destination_end - destination_start,
                source_end - source_start,
            )
            if copy_length > 0:
                far[destination_start:destination_start + copy_length] = samples[
                    source_start:source_start + copy_length
                ]

        return far

    def process_microphone(self, data: bytes) -> bytes:
        if not self.enabled or not data or len(data) % 2:
            return data
        near = np.frombuffer(data, dtype=np.int16)
        if not len(near):
            return data

        capture_end = time.monotonic()
        capture_start = capture_end - len(near) / SEND_SAMPLE_RATE

        with self._lock:
            far = self._reference_for_interval(capture_start, capture_end)
            try:
                cleaned = self._processor.process(near, far)
            except Exception as exc:
                print(f"[E.V.A] ⚠️ AEC emalı uğursuz oldu: {exc}", flush=True)
                return data

        return np.asarray(cleaned, dtype=np.int16).tobytes()

    def reset(self):
        with self._lock:
            self._far_segments.clear()
            self._playback_cursor = None
            if self._processor is not None:
                try:
                    self._processor.reset()
                except Exception:
                    pass


def apply_gain(data: bytes, gain: float) -> bytes:
    gain = max(0.0, min(1.0, float(gain)))
    if gain >= 0.999 or not data:
        return data
    sample_count = len(data) // 2
    if sample_count <= 0:
        return data
    samples = struct.unpack(f"<{sample_count}h", data[: sample_count * 2])
    adjusted = [max(-32768, min(32767, int(sample * gain))) for sample in samples]
    return struct.pack(f"<{sample_count}h", *adjusted) + data[sample_count * 2 :]


def create_audio() -> pyaudio.PyAudio:
    """Proses üçün PyAudio idarəedicisi yaradır."""
    return pyaudio.PyAudio()


_echo_canceller = _RealtimeEchoCanceller()
_output_interrupt_generation = 0
_last_playback_activity_at = 0.0
_PLAYBACK_ACTIVITY_GRACE_SECONDS = 0.35


def is_playback_active() -> bool:
    return time.monotonic() - _last_playback_activity_at < _PLAYBACK_ACTIVITY_GRACE_SECONDS


def get_output_interrupt_generation() -> int:
    return _output_interrupt_generation


def interrupt_output_stream():
    global _output_interrupt_generation, _last_playback_activity_at
    _output_interrupt_generation += 1
    _last_playback_activity_at = 0.0
    _echo_canceller.reset()


async def open_input_stream(audio):
    return await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )


async def open_output_stream(audio):
    stream = await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        output=True,
        rate=RECV_SAMPLE_RATE,
        frames_per_buffer=PLAYBACK_CHUNK_SIZE,
    )
    return stream


async def read_chunk(stream, size: int = CHUNK_SIZE) -> bytes:
    data = await asyncio.to_thread(
        stream.read,
        size,
        exception_on_overflow=False,
    )
    return _echo_canceller.process_microphone(data)


async def write_chunk(stream, data: bytes, gain: float = 1.0) -> None:
    global _last_playback_activity_at
    if gain < 0.999:
        data = apply_gain(data, gain)
    _echo_canceller.add_playback_reference(data)
    _last_playback_activity_at = time.monotonic()
    generation = get_output_interrupt_generation()
    try:
        await asyncio.to_thread(
            stream.write,
            data,
            exception_on_underflow=False,
        )
    except Exception:
        if get_output_interrupt_generation() != generation:
            return
        raise
