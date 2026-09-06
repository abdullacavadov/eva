import asyncio

from core.audio import open_input_stream, open_output_stream, read_chunk, write_chunk
from core.config import CHUNK_SIZE, PLAYBACK_CHUNK_SIZE, RECV_SAMPLE_RATE, SEND_SAMPLE_RATE


class _FakeAudio:
    def __init__(self):
        self.calls = []

    def open(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "stream"


class _FakeStream:
    def __init__(self):
        self.read_calls = []
        self.write_calls = []

    def read(self, *args, **kwargs):
        self.read_calls.append((args, kwargs))
        return b"pcm"

    def write(self, *args, **kwargs):
        self.write_calls.append((args, kwargs))


def test_input_stream_uses_realtime_capture_configuration():
    audio = _FakeAudio()

    stream = asyncio.run(open_input_stream(audio))

    assert stream == "stream"
    _, kwargs = audio.calls[-1]
    assert kwargs["rate"] == SEND_SAMPLE_RATE
    assert kwargs["frames_per_buffer"] == CHUNK_SIZE
    assert kwargs["input"] is True


def test_output_stream_uses_20ms_playback_buffer():
    audio = _FakeAudio()

    stream = asyncio.run(open_output_stream(audio))

    assert stream == "stream"
    _, kwargs = audio.calls[-1]
    assert kwargs["rate"] == RECV_SAMPLE_RATE
    assert kwargs["frames_per_buffer"] == PLAYBACK_CHUNK_SIZE
    assert PLAYBACK_CHUNK_SIZE == 480
    assert kwargs["output"] is True


def test_read_chunk_disables_input_overflow_errors():
    stream = _FakeStream()

    result = asyncio.run(read_chunk(stream))

    assert result == b"pcm"
    args, kwargs = stream.read_calls[-1]
    assert args == (CHUNK_SIZE,)
    assert kwargs["exception_on_overflow"] is False


def test_write_chunk_disables_output_underflow_errors():
    stream = _FakeStream()

    asyncio.run(write_chunk(stream, b"pcm"))

    args, kwargs = stream.write_calls[-1]
    assert args == (b"pcm",)
    assert kwargs["exception_on_underflow"] is False
