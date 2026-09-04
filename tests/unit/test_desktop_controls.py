import sys
import types

import pytest

from actions import desktop_controls
from actions.sys_info import sys_info


def test_set_volume_clamps_and_sets_scalar(monkeypatch):
    calls = []

    class Endpoint:
        def SetMasterVolumeLevelScalar(self, value, event):
            calls.append((value, event))

    class Device:
        EndpointVolume = Endpoint()

    monkeypatch.setitem(
        sys.modules,
        "pycaw.pycaw",
        types.SimpleNamespace(AudioUtilities=types.SimpleNamespace(GetSpeakers=lambda: Device())),
    )
    assert desktop_controls.set_volume(140) == "Səs səviyyəsi %100 olaraq təyin edildi."
    assert calls == [(1.0, None)]


def test_adjust_volume_uses_current_level(monkeypatch):
    monkeypatch.setattr(desktop_controls, "_volume_level", lambda: 95)
    monkeypatch.setattr(desktop_controls, "set_volume", lambda value: f"set:{value}")
    assert desktop_controls.adjust_volume(10) == "set:105.0"


def test_sys_info_routes_volume_and_brightness(monkeypatch):
    monkeypatch.setattr("actions.desktop_controls.get_volume", lambda: "Səs səviyyəsi %40-dir.")
    monkeypatch.setattr("actions.desktop_controls.get_brightness", lambda: "Ekran parlaqlığı təxminən %60-dir.")
    assert sys_info("volume") == "Səs səviyyəsi %40-dir."
    assert sys_info("brightness") == "Ekran parlaqlığı təxminən %60-dir."


def test_invalid_level_is_rejected():
    with pytest.raises(ValueError):
        sys_info("volume_set:not-a-number")
