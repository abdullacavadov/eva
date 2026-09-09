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

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
PLAYBACK_CHUNK_SIZE = 768


class _RealtimeEchoCanceller:
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
        if not self.enabled or not data or len(data) % 2:
            return data
        near = np.frombuffer(data, dtype=np.int16)
        if not len(near):
            return data
        with self._lock:
            mic_end = self._mic_position + len(near)
            self._append_silence_until(mic_end)
            reference_end = mic_end - round(
                SEND_SAMPLE_RATE * self._delay_ms / 1000
            )
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
            self._mic_position = mic_end
            try:
                cleaned = self._processor.process(near, far)
            except Exception as exc:
                print(f"[E.V.A] ⚠️ AEC emalı uğursuz oldu: {exc}", flush=True)
                return data
        return np.asarray(cleaned, dtype=np.int16).tobytes()

    def reset(self):
        with self._lock:
            self._far_reference = np.zeros(0, dtype=np.int16)
            self._far_base_position = 0
            self._far_position = 0
            self._mic_position = 0


def apply_gain(data: bytes, gain: float) -> bytes:
    if gain >= 0.999:
        return data
    samples = struct.unpack(f"<{len(data) // 2}h", data[: len(data) - len(data) % 2])
    adjusted = [max(-32768, min(32767, int(sample * gain))) for sample in samples]
    return struct.pack(f"<{len(adjusted)}h", *adjusted) + data[len(samples) * 2 :]

def create_audio() -> pyaudio.PyAudio:
    """Proses üçün PyAudio idarəedicisi yaradır."""
    return pyaudio.PyAudio()

_echo_canceller = _RealtimeEchoCanceller()
_output_interrupt_generation = 0


def get_output_interrupt_generation() -> int:
    return _output_interrupt_generation


def interrupt_output_stream():
    global _output_interrupt_generation
    _output_interrupt_generation += 1
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
        rate=RECV_SAMPLE_RATE,
        output=True,
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
