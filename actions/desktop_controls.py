"""Windows desktop controls: master volume and display brightness."""

from __future__ import annotations


def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _volume_level() -> int:
    from pycaw.pycaw import AudioUtilities  # type: ignore

    device = AudioUtilities.GetSpeakers()
    endpoint = device.EndpointVolume
    return _clamp(float(endpoint.GetMasterVolumeLevelScalar()) * 100)


def set_volume(value: int | float) -> str:
    """Set Windows master volume to a bounded 0..100 percentage."""
    from pycaw.pycaw import AudioUtilities  # type: ignore

    target = _clamp(float(value))
    device = AudioUtilities.GetSpeakers()
    endpoint = device.EndpointVolume
    endpoint.SetMasterVolumeLevelScalar(target / 100.0, None)
    return f"Səs səviyyəsi %{target} olaraq təyin edildi."


def adjust_volume(delta: int | float) -> str:
    """Adjust Windows master volume by a bounded percentage delta."""
    return set_volume(_volume_level() + float(delta))


def get_volume() -> str:
    return f"Səs səviyyəsi %{_volume_level()}-dir."


def _brightness_levels() -> list[int]:
    import screen_brightness_control as sbc  # type: ignore

    values = sbc.get_brightness()
    if isinstance(values, (int, float)):
        return [_clamp(float(values))]
    return [_clamp(float(v)) for v in values if isinstance(v, (int, float))]


def set_brightness(value: int | float) -> str:
    """Set brightness on all available displays to a bounded 0..100 value."""
    import screen_brightness_control as sbc  # type: ignore

    target = _clamp(float(value))
    sbc.set_brightness(target)
    return f"Ekran parlaqlığı %{target} olaraq təyin edildi."


def adjust_brightness(delta: int | float) -> str:
    levels = _brightness_levels()
    if not levels:
        raise RuntimeError("Ekran parlaqlığı oxuna bilmədi.")
    return set_brightness(sum(levels) / len(levels) + float(delta))


def get_brightness() -> str:
    levels = _brightness_levels()
    if not levels:
        raise RuntimeError("Ekran parlaqlığı oxuna bilmədi.")
    average = _clamp(sum(levels) / len(levels))
    return f"Ekran parlaqlığı təxminən %{average}-dir."
