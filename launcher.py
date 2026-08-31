"""E.V.A üçün vahid Windows launcher.

Bütün shortcut/autostart girişləri main.py-dən əvvəl bu launcher-i çağırır.
Startup SFX UI yaradıldıqdan sonra bir dəfə səslənir.
"""

from __future__ import annotations

from ui import JarvisUI


_original_init = JarvisUI.__init__


def _play_startup_sfx(self) -> None:
    """Start.mp3-ü startup zamanı bir dəfə və SFX toggle-ına hörmət edərək çal."""
    if getattr(self, "_startup_sfx_played", False):
        return
    self._startup_sfx_played = True
    if getattr(self, "_sfx_on", True) and getattr(self, "sound", None) is not None:
        self.sound.play_startup()


def _init_with_startup_sfx(self, *args, **kwargs):
    _original_init(self, *args, **kwargs)
    # _effects_active init zamanı hələ qurulmaya bilər; birbaşa _sfx_on yoxlanır.
    self.root.after(0, self._startup_sfx_callback)


def _startup_sfx_callback(self) -> None:
    _play_startup_sfx(self)


JarvisUI._startup_sfx_callback = _startup_sfx_callback
JarvisUI.__init__ = _init_with_startup_sfx


def main() -> None:
    import main as eva_main
    eva_main.main()


if __name__ == "__main__":
    main()
