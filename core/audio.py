"""Audio stream helpers for EVA's realtime voice runtime."""

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
    """Create the process-level PyAudio manager."""
    return pyaudio.PyAudio()


async def open_input_stream(audio: pyaudio.PyAudio):
    """Open EVA's microphone stream without blocking the event loop."""
    return await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )


async def open_output_stream(audio: pyaudio.PyAudio):
    """Open EVA's speaker stream without blocking the event loop."""
    return await asyncio.to_thread(
        audio.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=RECV_SAMPLE_RATE,
        output=True,
    )


async def read_chunk(stream, size: int = CHUNK_SIZE) -> bytes:
    """Read one microphone chunk in a worker thread."""
    return await asyncio.to_thread(
        stream.read,
        size,
        exception_on_overflow=False,
    )


async def write_chunk(stream, data: bytes) -> None:
    """Write one speaker chunk in a worker thread."""
    await asyncio.to_thread(stream.write, data)
