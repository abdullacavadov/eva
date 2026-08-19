"""EVA-nın real vaxt səs axını üçün köməkçi funksiyalar."""

import asyncio

import pyaudio

from core.config import (
    CHANNELS,
    CHUNK_SIZE,
    FORMAT,
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
    )


async def read_chunk(stream, size: int = CHUNK_SIZE) -> bytes:
    """Mikrofon axınından bir hissəni ayrıca worker thread-də oxuyur."""
    return await asyncio.to_thread(
        stream.read,
        size,
        exception_on_overflow=False,
    )


async def write_chunk(stream, data: bytes) -> None:
    """Səs hissəsini ayrıca worker thread-də dinamik axınına yazır."""
    await asyncio.to_thread(stream.write, data)
