"""EVA-nın real vaxt səs axını üçün köməkçi funksiyalar."""

import asyncio
import struct
import threading

import pyaudio

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
    """Mikrofon axınından bir hissəni ayrıca worker thread-də oxuyur."""
    return await asyncio.to_thread(
        stream.read,
        size,
        exception_on_overflow=False,
    )


def get_output_interrupt_generation() -> int:
    """Cari playback interruption nəsil nömrəsini qaytarır."""
    with _output_stream_lock:
        return _output_interrupt_generation


def interrupt_output_stream() -> bool:
    """Cari playback-i dərhal dayandırıb stream-i yenidən aktiv edir."""
    global _output_stream_interrupt_generation, _active_output_stream
    with _output_stream_lock:
        stream = _active_output_stream
        global _output_interrupt_generation
        _output_interrupt_generation += 1
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
    """Səs hissəsini qazanc tətbiq edib ayrıca worker thread-də səsləndirir."""
    if gain < 0.999:
        data = apply_gain(data, gain)
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
