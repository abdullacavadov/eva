"""EVA-nın real vaxt səs axını üçün köməkçi funksiyalar."""

import asyncio
import struct

import pyaudio

from core.config import (
    CHANNELS,
    CHUNK_SIZE,
    FORMAT,
    PLAYBACK_CHUNK_SIZE,
    RECV_SAMPLE_RATE,
    SEND_SAMPLE_RATE,
)


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
    return await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=RECV_SAMPLE_RATE,
        output=True,
        frames_per_buffer=PLAYBACK_CHUNK_SIZE,
    )


async def read_chunk(stream, size: int = CHUNK_SIZE) -> bytes:
    """Mikrofon axınından bir hissəni ayrıca worker thread-də oxuyur."""
    return await asyncio.to_thread(
        stream.read,
        size,
        exception_on_overflow=False,
    )


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
    await asyncio.to_thread(
        stream.write,
        data,
        exception_on_underflow=False,
    )
