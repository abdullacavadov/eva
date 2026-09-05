import struct

from wakeup_listener import WakeGestureListener


def _pcm_with_level(level: int, samples: int = 1024) -> bytes:
    return struct.pack(f"<{samples}h", *([level] * samples))


def test_double_clap_triggers_after_two_distinct_impulses():
    wakes = []
    listener = WakeGestureListener(on_wake=lambda: wakes.append(True))
    listener.process_chunk(_pcm_with_level(5000), now=0.0)
    listener.process_chunk(_pcm_with_level(5000), now=0.05)
    listener.process_chunk(_pcm_with_level(0), now=0.10)
    listener.process_chunk(_pcm_with_level(5000), now=0.30)
    assert wakes == [True]


def test_same_clap_spanning_multiple_chunks_counts_once():
    wakes = []
    listener = WakeGestureListener(on_wake=lambda: wakes.append(True))
    listener.process_chunk(_pcm_with_level(5000), now=0.0)
    listener.process_chunk(_pcm_with_level(5000), now=0.05)
    listener.process_chunk(_pcm_with_level(0), now=0.10)
    assert wakes == []


def test_second_clap_after_window_does_not_trigger():
    wakes = []
    listener = WakeGestureListener(on_wake=lambda: wakes.append(True))
    listener.process_chunk(_pcm_with_level(5000), now=0.0)
    listener.process_chunk(_pcm_with_level(0), now=0.20)
    listener.process_chunk(_pcm_with_level(5000), now=2.10)
    assert wakes == []
