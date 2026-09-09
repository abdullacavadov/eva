"""EVA-nın real vaxt səs axını üçün köməkçi funksiyalar."""

import asyncio
import os
import struct
import threading

import numpy as np
import pyaudio

try:
    from pywebrtc_audio import AudioProcessor
except Exception:
    AudioProcessor = None

from core.config import (
    CHANNELS,
    CHUNK_SIZE,
    FORMAT,
    PLAYBACK_CHUNK_SIZE,
    RECV_SAMPLE_RATE,
    SEND_SAMPLE_RATE,
)


_active_output_stream = None
_output_stream_lock = threading.Lock()
_output_interrupt_generation = 0


class _RealtimeEchoCanceller:
    """Mikrofon siqnalından EVA-nın səsgücləndirici əks-sədasını WebRTC AEC3 ilə süzür."""

    def __init__(self):
        self._lock = threading.Lock()
        self._processor = None
        self._far_reference = np.zeros(0, dtype=np.int16)
        self._far_base_position = 0
        self._far_position = 0
        self._mic_position = 0
        self._delay_ms = max(0, int(os.getenv("EVA_AEC_DELAY_MS", "60")))
        self._max_reference_samples = SEND_SAMPLE_RATE * 2
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
        if not self.enabled or not data:
            return
        reference = self._resample(data)
        if not len(reference):
            return
        with self._lock:
            self._far_reference = np.concatenate((self._far_reference, reference))
            self._far_position += len(reference)
            self._trim_reference()

    def _trim_reference(self):
        if len(self._far_reference) <= self._max_reference_samples:
            return
        trim = len(self._far_reference) - self._max_reference_samples
        self._far_reference = self._far_reference[trim:]
        self._far_base_position += trim

    def _append_silence_until(self, target_position: int):
        if target_position <= self._far_position:
            return
        missing = target_position - self._far_position
        self._far_reference = np.concatenate(
            (self._far_reference, np.zeros(missing, dtype=np.int16))
        )
        self._far_position = target_position
        self._trim_reference()

    def process_microphone(self, data: bytes) -> bytes:
        if not self.enabled or not data:
            return data
        near = np.frombuffer(data, dtype=np.int16)
        if not len(near):
            return data
        with self._lock:
            target_end = self._mic_position + len(near) - round(
                SEND_SAMPLE_RATE * self._delay_ms / 1000
            )
            self._append_silence_until(target_end)
            reference_end = target_end
            reference_start = reference_end - len(near)
            far_start = reference_start - self._far_base_position
            far_end = reference_end - self._far_base_position
            far = np.zeros(len(near), dtype=np.int16)
            source_start = max(0, far_start)
            source_end = min(len(self._far_reference), far_end)
            if source_end > source_start:
                destination_start = source_start - far_start
                destination_end = destination_start + (source_end - source_start)
                far[destination_start:destination_end] = self._far_reference[
                    source_start:source_end
                ]
            self._mic_position += len(near)
            try:
                cleaned = self._processor.process(near, far)
            except Exception as exc:
                print(f"[E.V.A] ⚠️ AEC emalı uğursuz oldu: {exc}", flush=True)
                return data
        return np.asarray(cleaned, dtype=np.int16).tobytes()

    def reset(self):
        if not self.enabled:
            return
        with self._lock:
            try:
                self._processor.reset()
            except Exception:
                pass
            self._far_reference = np.zeros(0, dtype=np.int16)
            self._far_base_position = 0
            self._far_position = 0
            self._mic_position = 0


_echo_canceller = _RealtimeEchoCanceller()


def create_audio() -> pyaudio.PyAudio:
    """Proses üçün PyAudio idarəedicisi yaradır."""
    return pyaudio.PyAudio()


async def open_input_stream(audio: pyaudio.PyAudio):
    """EVA-nın mikrofon axınını event loop-u bloklamadan açır."""
    return await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )


async def open_output_stream(audio: pyaudio.PyAudio):
    """EVA-nın dinamik axınını event loop-u bloklamadan açır."""
    stream = await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=RECV_SAMPLE_RATE,
        output=True,
        frames_per_buffer=PLAYBACK_CHUNK_SIZE,
    )
    global _active_output_stream
    with _output_stream_lock:
        _active_output_stream = stream
    return stream


async def read_chunk(stream, size: int = CHUNK_SIZE) -> bytes:
    """Mikrofon hissəsini oxuyur və EVA playback əks-sədasını AEC ilə təmizləyir."""
    data = await asyncio.to_thread(
        stream.read,
        size,
        exception_on_overflow=False,
    )
    return _echo_canceller.process_microphone(data)


def get_output_interrupt_generation() -> int:
    """Cari playback interruption nəsil nömrəsini qaytarır."""
    with _output_stream_lock:
        return _output_interrupt_generation


def interrupt_output_stream() -> bool:
    """Cari playback-i dərhal dayandırıb stream-i yenidən aktiv edir."""
    global _active_output_stream, _output_interrupt_generation
    with _output_stream_lock:
        stream = _active_output_stream
        _output_interrupt_generation += 1
    _echo_canceller.reset()
    if stream is None:
        return False

    try:
        abort = getattr(stream, "abort_stream", None)
        if callable(abort):
            abort()
        else:
            stream.stop_stream()
        start = getattr(stream, "start_stream", None)
        if callable(start) and not stream.is_active():
            start()
        return True
    except Exception:
        try:
            stream.stop_stream()
            stream.start_stream()
            return True
        except Exception:
            return False


def clear_output_stream(stream) -> None:
    """Aktiv playback stream qeydini təhlükəsiz şəkildə təmizləyir."""
    global _active_output_stream
    with _output_stream_lock:
        if _active_output_stream is stream:
            _active_output_stream = None


def apply_gain(data: bytes, gain: float) -> bytes:
    """16-bit PCM chunk-a proqram səviyyəsində səs qazancı tətbiq edir."""
    gain = max(0.0, min(1.0, float(gain)))
    if gain >= 0.999 or not data:
        return data
    sample_count = len(data) // 2
    if sample_count <= 0:
        return data
    samples = struct.unpack(f"<{sample_count}h", data[: sample_count * 2])
    scaled = [max(-32768, min(32767, int(sample * gain))) for sample in samples]
    return struct.pack(f"<{sample_count}h", *scaled)


async def write_chunk(stream, data: bytes, gain: float = 1.0) -> None:
    """Səs hissəsini səsləndirir və AEC üçün eyni playback referensini qeyd edir."""
    if gain < 0.999:
        data = apply_gain(data, gain)
    _echo_canceller.add_playback_reference(data)
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
