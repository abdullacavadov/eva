"""React runtime üçün Tkinter-dən asılı olmayan UI adapteri."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class _RuntimeRoot:
    """Legacy JarvisLive callback-ləri üçün minimal root contract."""

    def after(self, _delay_ms: int, callback: Callable[..., Any], *args: Any) -> None:
        callback(*args)

    def withdraw(self) -> None:
        return None


class RuntimeUI:
    """JarvisLive/ToolExecutor üçün headless UI contract.

    Tkinter, desktop window, legacy orb və desktop SFX player yaratmır.
    Hadisələr UiBridge vasitəsilə React UI-a ötürülür.
    """

    _STATE_SFX = {"IDLE": "Start", "THINKING": "Think", "SUCCESS": "Done", "ERROR": "Error"}

    def __init__(self) -> None:
        self.root = _RuntimeRoot()
        self.muted = False
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_effects_state_change = None
        self.on_webcam_toggle = None
        self.emit_event: Callable[..., Any] = lambda *_args, **_kwargs: None
        self._state = "IDLE"
        self._webcam_active = False

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        self._state = str(state or "IDLE")
        sfx = self._STATE_SFX.get(self._state)
        if sfx:
            self.emit_event("sfx.play", name=sfx)

    def write_log(self, text: str) -> None:
        return None

    def write_debug(self, text: str, level: str = "INFO") -> None:
        self.emit_event("debug.created", message=str(text), level=str(level))

    def mark_user_activity(self, active: bool = True) -> None:
        self.emit_event("user.activity", active=bool(active))

    def focus_panel(self, panel: str, duration_ms: int = 0) -> None:
        self.emit_event("panel.focus", panel=str(panel), duration_ms=int(duration_ms))

    def set_webcam_active(self, active: bool) -> None:
        self._webcam_active = bool(active)
        self.emit_event("webcam.changed", active=self._webcam_active)

    def update_webcam_preview(self, _jpeg: bytes) -> None:
        return None

    def play_success_sfx(self) -> None:
        self.emit_event("sfx.play", name="Done")

    def play_sfx(self, name: str) -> None:
        self.emit_event("sfx.play", name=str(name))

    def wait_for_api_key(self) -> None:
        return None
