"""React runtime üçün Tkinter-dən asılı olmayan UI adapteri."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class _RuntimeRoot:
    """Legacy JarvisLive callback-ləri üçün minimal Tk uyğunluğu."""

    def after(self, _delay_ms: int, callback: Callable[..., Any], *args: Any) -> None:
        callback(*args)

    def withdraw(self) -> None:
        return None


class RuntimeUI:
    """JarvisLive/ToolExecutor üçün headless UI contract.

    Bu adapter ui.py import etmir və Tkinter, pəncərə, desktop orb və SFX
    playback yaratmır. Hadisələr UiBridge tərəfindən React-a ötürülür.
    """

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

    def write_log(self, text: str) -> None:
        # UiBridge hook-u bunu React activity/conversation eventinə çevirir.
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
        # React runtime üçün preview kanalı ayrıca əlavə edilə bilər; Tk preview
        # kimi hər frame-i UI thread-inə daşımırıq.
        return None

    def play_success_sfx(self) -> None:
        self.emit_event("sfx.play", name="Done")

    def play_sfx(self, name: str) -> None:
        self.emit_event("sfx.play", name=str(name))

    def wait_for_api_key(self) -> None:
        # API key artıq core.config.get_api_key() tərəfindən idarə olunur.
        return None
