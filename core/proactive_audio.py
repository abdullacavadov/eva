"""Proaktiv bildirişlərin audio çatdırılması üçün təhlükəsiz policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProactiveAudioPolicy:
    """Proaktiv TTS-in EVA-nın aktiv səsini kəsməsinin qarşısını alır."""

    enabled: bool = True
    interrupt_speaking: bool = False
    respect_mute: bool = True
    respect_pause: bool = True

    def should_speak(self, *, speaking: bool, muted: bool, paused: bool) -> bool:
        if not self.enabled:
            return False
        if self.respect_pause and paused:
            return False
        if self.respect_mute and muted:
            return False
        if speaking and not self.interrupt_speaking:
            return False
        return True

    def choose_text(self, event: dict) -> str:
        return str(event.get("text") or event.get("title") or "Proaktiv bildiriş").strip()
