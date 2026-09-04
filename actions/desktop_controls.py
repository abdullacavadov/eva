"""Windows desktop controls: master volume and display brightness."""

from __future__ import annotations

import json
import subprocess


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
    actual = _volume_level()
    return f"Səs səviyyəsi %{actual} olaraq təyin edildi."


def adjust_volume(delta: int | float) -> str:
    """Adjust Windows master volume by a bounded percentage delta."""
    return set_volume(_volume_level() + float(delta))


def get_volume() -> str:
    return f"Səs səviyyəsi %{_volume_level()}-dir."


def _brightness_levels() -> list[int]:
    """Read brightness, preferring screen-brightness-control with a WMI fallback."""
    try:
        import screen_brightness_control as sbc  # type: ignore

        values = sbc.get_brightness()
        if isinstance(values, (int, float)):
            return [_clamp(float(values))]
        levels = [_clamp(float(v)) for v in values if isinstance(v, (int, float))]
        if levels:
            return levels
    except (ImportError, OSError, RuntimeError, subprocess.SubprocessError):
        pass

    try:
        script = (
            "Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness "
            "| Select-Object -ExpandProperty CurrentBrightness | ConvertTo-Json -Compress"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).strip()
        if not output:
            return []
        values = json.loads(output)
        if not isinstance(values, list):
            values = [values]
        return [_clamp(float(v)) for v in values if isinstance(v, (int, float))]
    except (OSError, ValueError, TypeError, subprocess.SubprocessError, json.JSONDecodeError):
        return []


def _set_brightness_wmi(target: int) -> bool:
    """Set physical display brightness without requiring an extra Python package."""
    script = (
        "$targets = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods; "
        "if (-not $targets) { exit 2 }; "
        f"$targets | ForEach-Object {{ $_.WmiSetBrightness(1, {target}) }}"
    )
    try:
        subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def set_brightness(value: int | float) -> str:
    """Set brightness on all available displays to a bounded 0..100 value."""
    target = _clamp(float(value))
    try:
        import screen_brightness_control as sbc  # type: ignore

        sbc.set_brightness(target)
    except (ImportError, OSError, RuntimeError, subprocess.SubprocessError):
        if not _set_brightness_wmi(target):
            raise RuntimeError("Ekran parlaqlığı üçün uyğun Windows monitor interfeysi tapılmadı.")

    levels = _brightness_levels()
    actual = _clamp(sum(levels) / len(levels)) if levels else target
    return f"Ekran parlaqlığı %{actual} olaraq təyin edildi."


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
