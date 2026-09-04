"""Windows desktop controls: master volume and display brightness."""

from __future__ import annotations

import subprocess


def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _volume_endpoint():
    from pycaw.pycaw import AudioUtilities  # type: ignore

    device = AudioUtilities.GetSpeakers()
    return device.EndpointVolume


def _volume_level() -> int:
    endpoint = _volume_endpoint()
    return _clamp(float(endpoint.GetMasterVolumeLevelScalar()) * 100)


def set_volume(value: int | float) -> str:
    """Set Windows master volume to a bounded 0..100 percentage."""
    target = _clamp(float(value))
    endpoint = _volume_endpoint()
    endpoint.SetMasterVolumeLevelScalar(target / 100.0, None)

    getter = getattr(endpoint, "GetMasterVolumeLevelScalar", None)
    if callable(getter):
        actual = _clamp(float(getter()) * 100)
        if abs(actual - target) > 1:
            raise RuntimeError(
                f"Windows səs səviyyəsi dəyişmədi: %{actual} olaraq qaldı."
            )
        return f"Səs səviyyəsi %{actual} olaraq təyin edildi."
    return f"Səs səviyyəsi %{target} olaraq təyin edildi."


def adjust_volume(delta: int | float) -> str:
    """Adjust Windows master volume by a bounded percentage delta."""
    return set_volume(_volume_level() + float(delta))


def get_volume() -> str:
    return f"Səs səviyyəsi %{_volume_level()}-dir."


def _brightness_levels_sbc() -> list[int]:
    import screen_brightness_control as sbc  # type: ignore

    values = sbc.get_brightness()
    if isinstance(values, (int, float)):
        return [_clamp(float(values))]
    return [_clamp(float(v)) for v in values if isinstance(v, (int, float))]


def _brightness_levels_powershell() -> list[int]:
    command = (
        "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness "
        "| Select-Object -ExpandProperty CurrentBrightness"
    )
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        text=True,
        timeout=8,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
    )
    levels: list[int] = []
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            levels.append(_clamp(float(line)))
    return levels


def _brightness_levels() -> list[int]:
    try:
        return _brightness_levels_sbc()
    except (ImportError, ModuleNotFoundError):
        return _brightness_levels_powershell()


def _brightness_matches_target(target: int, tolerance: int = 2) -> bool:
    try:
        levels = _brightness_levels()
    except Exception:
        return False
    if not levels:
        return False
    average = sum(levels) / len(levels)
    return abs(average - target) <= tolerance


def _set_brightness_sbc(target: int) -> None:
    import screen_brightness_control as sbc  # type: ignore

    sbc.set_brightness(target)


def _set_brightness_powershell(target: int) -> None:
    command = (
        "$methods=Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods; "
        "if (-not $methods) { throw 'Windows brightness method provider tapılmadı.' }; "
        f"$methods | ForEach-Object {{ $_.WmiSetBrightness(1,{target}) }}"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        timeout=8,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def set_brightness(value: int | float) -> str:
    """Set brightness on available Windows displays to a bounded 0..100 value."""
    target = _clamp(float(value))
    errors_seen: list[str] = []

    # Prefer the dedicated library, but do not trust a successful call blindly.
    # Some Windows/display combinations accept the call while leaving the
    # reported brightness unchanged. In that case try the native WMI backend.
    try:
        _set_brightness_sbc(target)
        if _brightness_matches_target(target):
            return f"Ekran parlaqlığı %{target} olaraq təyin edildi."
        errors_seen.append("screen_brightness_control dəyişiklikdən sonra dəyəri təsdiqləmədi")
    except (ImportError, ModuleNotFoundError) as exc:
        errors_seen.append(f"screen_brightness_control yoxdur: {exc}")
    except Exception as exc:
        errors_seen.append(f"screen_brightness_control: {exc}")

    try:
        _set_brightness_powershell(target)
        if _brightness_matches_target(target):
            return f"Ekran parlaqlığı %{target} olaraq təyin edildi."
        errors_seen.append("PowerShell WMI dəyişiklikdən sonra dəyəri təsdiqləmədi")
    except Exception as exc:
        errors_seen.append(f"PowerShell WMI: {exc}")

    try:
        actual_levels = _brightness_levels()
    except Exception:
        actual_levels = []
    if actual_levels:
        actual = _clamp(sum(actual_levels) / len(actual_levels))
        raise RuntimeError(
            f"Windows ekran parlaqlığı dəyişmədi: təxminən %{actual} olaraq qaldı."
        )
    detail = "; ".join(errors_seen)
    raise RuntimeError(f"Windows ekran parlaqlığı təyin edilə bilmədi. {detail}")


def adjust_brightness(delta: int | float) -> str:
    levels = _brightness_levels()
    if not levels:
        raise RuntimeError("Ekran parlaqlığı oxunə bilmədi.")
    return set_brightness(sum(levels) / len(levels) + float(delta))


def get_brightness() -> str:
    levels = _brightness_levels()
    if not levels:
        raise RuntimeError("Ekran parlaqlığı oxunə bilmədi.")
    average = _clamp(sum(levels) / len(levels))
    return f"Ekran parlaqlığı təxminən %{average}-dir."