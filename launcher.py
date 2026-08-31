"""E.V.A üçün vahid Windows launcher.

Bütün shortcut/autostart girişləri main.py-dən əvvəl bu launcher-i çağırır.
Beləliklə startup SFX UI yaradıldıqdan dərhal sonra, yalnız bir dəfə səslənir.
"""

from __future__ import annotations

from ui import JarvisUI


_original_init = JarvisUI.__init__


def _init_with_startup_sfx(self, *args, **kwargs):
    _original_init(self, *args, **kwargs)
    # UI tam qurulduqdan sonra və əsas runtime thread başlamazdan əvvəl.
    self.root.after(0, self._play_startup_sfx_once)


JarvisUI.__init__ = _init_with_startup_sfx


def main() -> None:
    # Import burada edilir ki, main.py JarvisUI patch edildikdən sonra işləsin.
    import main as eva_main

    eva_main.main()


if __name__ == "__main__":
    main()
