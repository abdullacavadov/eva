from pathlib import Path


def test_startup_sfx_asset_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "SFX" / "Start.mp3").is_file()


def test_startup_sfx_is_triggered_from_ui_initialisation():
    root = Path(__file__).resolve().parents[1]
    ui = (root / "ui.py").read_text(encoding="utf-8")
    marker = 'self._enter_fullscreen()\n        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)'
    assert marker in ui
    assert "self._play_startup_sfx_once()" in ui
    assert ui.index("self._play_startup_sfx_once()") > ui.index("self._enter_fullscreen()")
