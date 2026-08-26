"""
EVA Windows — UI v3
Concentric teal rings · Segmented arcs
"""

import subprocess as _sp
import os
import time
import math
import random
import threading
import tkinter as tk
from collections import deque
from pathlib import Path
import psutil

from PIL import Image, ImageTk, ImageDraw, ImageFont
from app_config import has_gemini_api_key, load_app_config, save_app_config
from actions.weather import get_weather_summary

BASE_DIR = Path(__file__).resolve().parent

SYSTEM_NAME = "E.V.A"
MODEL_BADGE = "Core for Windows"

# ── Renk paleti ──────────────────────────────────────────────────────────────
C_BG = "#020c0c"
C_PRI = "#00d4c0"
C_ORG = "#ff6600"
C_ORG2 = "#ff9900"
C_MID = "#006a62"
C_DIM = "#0a2a28"
C_DIMMER = "#061414"
C_TEXT = "#7dfff6"
C_PANEL = "#030f0f"
C_GREEN = "#00ff88"
C_RED = "#ff3344"
C_MUTED = "#cc2255"
C_BLUE = "#4488ff"
C_GOLD = "#ffcc00"

ORB_COLORS = {
    "LISTENING": (0, 255, 136),
    "SPEAKING": (68, 136, 255),
    "THINKING": (255, 204, 0),
    "MUTED": (200, 30, 80),
    "PAUSED": (30, 60, 55),
    "ERROR": (255, 51, 68),
    "INITIALISING": (255, 51, 68),
}

W_TARGET = 1540
H_TARGET = 940
LEFT_W_T = 310
RIGHT_W_T = 340
HDR_H = 72
FOOTER_H = 26
INPUT_H = 34
CONTROL_H = 126

VOICES = ["Charon", "Puck", "Aoede", "Kore",
          "Fenrir", "Leda", "Orus", "Zephyr"]

FONT_BODY_FAMILY = "Grift"
FONT_DISPLAY_FAMILY = "Grift Extra Bold"


def font_body(size: int):
    return (FONT_BODY_FAMILY, size)


def font_body_bold(size: int):
    return (FONT_BODY_FAMILY, size, "bold")


def font_display(size: int):
    return (FONT_DISPLAY_FAMILY, size)


STATE_HEX_COLORS = {
    "LISTENING": C_GREEN,
    "SPEAKING": C_BLUE,
    "THINKING": C_GOLD,
    "INITIALISING": C_RED,
    "ERROR": C_RED,
}


def _resolve_sfx_dir() -> Path:
    return BASE_DIR / "SFX"


_SFX_DIR = _resolve_sfx_dir()
_HUD_FILE = _SFX_DIR / "HUD.mp3"
_START_FILE = _SFX_DIR / "Start.mp3"
_THINK_FILE = _SFX_DIR / "Think.mp3"
_DONE_FILE = _SFX_DIR / "Done.mp3"
_ERROR_FILE = _SFX_DIR / "Error.mp3"

_CREATE_NO_WINDOW = getattr(_sp, "CREATE_NO_WINDOW", 0)


def _play_audio_file(path: Path, volume: float):
    vol = max(0.0, min(1.0, float(volume)))
    uri = str(path).replace("\\", "/")
    script = (
        "Add-Type -AssemblyName presentationCore;"
        "$ErrorActionPreference='SilentlyContinue';"
        "$p=New-Object System.Windows.Media.MediaPlayer;"
        f"$p.Open([System.Uri]'{uri}');"
        f"$p.Volume={vol:.2f};"
        "$p.Play();"
        "$n=0; while(-not $p.NaturalDuration.HasTimeSpan -and $n -lt 40){Start-Sleep -Milliseconds 50; $n++};"
        "if($p.NaturalDuration.HasTimeSpan)"
        "{Start-Sleep -Milliseconds ([int]$p.NaturalDuration.TimeSpan.TotalMilliseconds + 150)}"
        "else{Start-Sleep -Seconds 5}"
    )
    return _sp.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
        stdout=_sp.DEVNULL,
        stderr=_sp.DEVNULL,
        creationflags=_CREATE_NO_WINDOW,
    )


class SoundManager:
    def __init__(self):
        self._enabled = True
        self._ambient_proc = None
        self._volume = 0.20
        self._ambient_stop = None
        self._ambient_thread = None
        self._foreground_proc = None
        self._foreground_stop = None
        self._foreground_thread = None
        self._foreground_tag = ""
        self._lock = threading.Lock()

    @staticmethod
    def _terminate_process(proc):
        if not proc or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def start_ambient(self):
        if not _HUD_FILE.exists():
            return
        with self._lock:
            if not self._enabled:
                return
            if self._foreground_proc and self._foreground_proc.poll() is None:
                return
            if self._ambient_thread and self._ambient_thread.is_alive():
                return
            stop_event = threading.Event()
            worker = threading.Thread(target=self._loop_ambient, args=(stop_event,), daemon=True)
            self._ambient_stop = stop_event
            self._ambient_thread = worker
        worker.start()

    def _loop_ambient(self, stop_event: threading.Event):
        while not stop_event.is_set():
            with self._lock:
                if not self._enabled or self._ambient_stop is not stop_event:
                    break
                volume = self._volume
            try:
                proc = _play_audio_file(_HUD_FILE, volume)
            except Exception:
                break
            with self._lock:
                if self._ambient_stop is not stop_event or not self._enabled:
                    self._terminate_process(proc)
                    break
                self._ambient_proc = proc
            while proc.poll() is None and not stop_event.wait(0.2):
                pass
            if stop_event.is_set():
                self._terminate_process(proc)
            with self._lock:
                if self._ambient_proc is proc:
                    self._ambient_proc = None
            if stop_event.is_set():
                break
            time.sleep(0.2)
        with self._lock:
            if self._ambient_stop is stop_event:
                self._ambient_stop = None
            if self._ambient_thread and self._ambient_thread.ident == threading.get_ident():
                self._ambient_thread = None

    def _stop_ambient(self):
        with self._lock:
            stop_event = self._ambient_stop
            proc = self._ambient_proc
            self._ambient_stop = None
            self._ambient_thread = None
            self._ambient_proc = None
        if stop_event:
            stop_event.set()
        self._terminate_process(proc)

    def _stop_foreground(self):
        with self._lock:
            stop_event = self._foreground_stop
            proc = self._foreground_proc
            self._foreground_stop = None
            self._foreground_thread = None
            self._foreground_proc = None
            self._foreground_tag = ""
        if stop_event:
            stop_event.set()
        self._terminate_process(proc)

    def _play_foreground(self, path: Path, tag: str, loop: bool = False, volume_factor: float = 1.0, pause_ambient: bool = True):
        if not path.exists():
            return
        with self._lock:
            if not self._enabled:
                return
            if loop and self._foreground_tag == tag and self._foreground_thread and self._foreground_thread.is_alive():
                return
            base_volume = self._volume
        if pause_ambient:
            self._stop_ambient()
        self._stop_foreground()
        stop_event = threading.Event()
        worker = threading.Thread(target=self._foreground_worker, args=(path, tag, stop_event, loop, max(0.0, min(1.0, base_volume * volume_factor)), pause_ambient), daemon=True)
        with self._lock:
            self._foreground_stop = stop_event
            self._foreground_thread = worker
            self._foreground_tag = tag
        worker.start()

    def _foreground_worker(self, path: Path, tag: str, stop_event: threading.Event, loop: bool, volume: float, resume_ambient: bool):
        while not stop_event.is_set():
            try:
                proc = _play_audio_file(path, volume)
            except Exception:
                break
            with self._lock:
                if self._foreground_stop is not stop_event or not self._enabled:
                    self._terminate_process(proc)
                    break
                self._foreground_proc = proc
            while proc.poll() is None and not stop_event.wait(0.12):
                pass
            if stop_event.is_set():
                self._terminate_process(proc)
            with self._lock:
                if self._foreground_proc is proc:
                    self._foreground_proc = None
            if not loop or stop_event.is_set():
                break
            time.sleep(0.08)
        with self._lock:
            if self._foreground_stop is stop_event:
                self._foreground_stop = None
                self._foreground_thread = None
                self._foreground_tag = ""
            should_restart = resume_ambient and self._enabled and self._foreground_stop is None
        if should_restart:
            self.start_ambient()

    def play_startup(self):
        self._play_foreground(_START_FILE, tag="start", loop=False, volume_factor=0.95)

    def play_success(self):
        self._play_foreground(_DONE_FILE, tag="done", loop=False, volume_factor=0.68, pause_ambient=False)

    def play_error(self):
        self._play_foreground(_ERROR_FILE, tag="error", loop=False, volume_factor=0.95)

    def start_thinking(self):
        self._play_foreground(_THINK_FILE, tag="think", loop=True, volume_factor=0.82, pause_ambient=False)

    def stop_thinking(self):
        with self._lock:
            is_thinking = self._foreground_tag == "think"
        if is_thinking:
            self._stop_foreground()

    def toggle(self) -> bool:
        self.set_enabled(not self._enabled)
        return self._enabled

    def set_enabled(self, enabled: bool):
        enabled = bool(enabled)
        with self._lock:
            self._enabled = enabled
        if enabled:
            self.start_ambient()
        else:
            self._stop_ambient()
            self._stop_foreground()

    def set_volume(self, volume: float):
        with self._lock:
            self._volume = max(0.0, min(1.0, float(volume)))
            fg_tag = self._foreground_tag
            can_restart_ambient = self._enabled and not fg_tag
        if fg_tag == "think":
            self._stop_foreground()
            self.start_thinking()
        elif can_restart_ambient:
            self._stop_ambient()
            self.start_ambient()

    def stop_all(self):
        with self._lock:
            self._enabled = False
        self._stop_ambient()
        self._stop_foreground()

    def get_volume(self) -> float:
        return self._volume


class JarvisUI:
    def __init__(self, headless: bool = False):
        self._headless = bool(headless)
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("E.V.A")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.W = min(sw - 48, W_TARGET)
        self.H = min(sh - 84, H_TARGET)
        _geo = f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}"
        self.root.geometry(_geo)
        self.root.configure(bg=C_BG)

        self._window_geometry = _geo
        self._normal_size = (self.W, self.H)
        self._fullscreen = False
        self._resize_job = None
        self._set_layout_metrics(self.W, self.H)

        self.speaking = False
        self.user_speaking = False
        self.muted = False
        self.paused = False
        self.scale = 1.0
        self.target_scale = 1.0
        self.halo_a = 55.0
        self.target_halo = 55.0
        self.last_t = time.time()
        self.tick = 0
        self.rings_spin = [0.0, 45.0, 90.0, 200.0]
        self.pulse_r = []
        self.status_blink = True
        self._jarvis_state = "INITIALISING"
        self._user_speaking_until = 0.0

        self._webcam_active = False
        self._webcam_photo = None
        self._cam_label = None
        self._cam_orb_shift = 0.0
        self._cam_orb_shift_target = 0.0
        self._cam_orb_face = 0.0
        self._cam_orb_face_target = 0.0
        self._weather_card = {"city": "Baku", "primary": "--", "details": ["Hava durumu yüklənir..."]}
        self._panel_focus = ""
        self._panel_focus_until = 0.0
        self._brief_refresh_busy = False
        self._started_at = time.time()
        self._error_hold_until = 0.0
        self._settings_open = False
        self._settings_tab = "settings"
        self._debug_entries = deque(maxlen=160)
        self._startup_sfx_played = False
        self._settings_geometry = {"btn_x": 14, "btn_y": 12, "btn_w": 250, "btn_h": 46, "panel_x": 14, "panel_y": HDR_H + 10, "panel_w": 320, "panel_h": 390}
        self.setup_frame = None
        self.api_entry = None
        self.youtube_api_entry = None
        self.youtube_handle_entry = None

        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_stop_command = None
        self.on_voice_change = None
        self.on_effects_state_change = None
        self.on_webcam_toggle = None

        self._current_voice = self._load_voice()
        self.sound = SoundManager()
        self._stats = {'cpu': 0.0, 'ram': 0.0, 'disk': 0.0, 'battery': 100.0, 'net_up': 0.0, 'net_down': 0.0}
        self._cpu_hist = [0.0] * 24
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._wave_jarvis = [random.randint(4, 26) for _ in range(18)]
        self._wave_user = [random.randint(2, 10) for _ in range(18)]

        self.typing_queue = deque()
        self.is_typing = False
        self.particles = [{'x': random.uniform(0, self.W), 'y': random.uniform(0, self.H), 'vx': random.uniform(-0.15, 0.15), 'vy': random.uniform(-0.15, 0.15), 'r': random.uniform(0.5, 1.8), 'a': random.randint(15, 70)} for _ in range(24)]
        self.orb_particles = [{'angle': random.uniform(0, math.tau), 'orbit': random.uniform(0.06, 0.98), 'speed': random.uniform(-0.030, 0.030), 'size': random.uniform(0.8, 2.8), 'phase': random.uniform(0, math.tau), 'wobble': random.uniform(0.010, 0.040), 'depth': random.uniform(0.30, 1.00)} for _ in range(160)]
        self.orb_shell_particles = [{'angle': random.uniform(0, math.tau), 'speed': random.uniform(-0.020, 0.020), 'size': random.uniform(1.4, 3.8), 'phase': random.uniform(0, math.tau), 'glow': random.uniform(0.4, 1.0)} for _ in range(84)]

        self.bg = tk.Canvas(self.root, width=self.W, height=self.H, bg=C_BG, highlightthickness=0)
        self.bg.place(x=0, y=0)
        self.log_frame = tk.Frame(self.root, bg="#030e0e", highlightbackground=C_MID, highlightthickness=1)
        self.log_frame.place(x=self.CHAT_X, y=self.CHAT_Y, width=self.CHAT_W, height=self.CHAT_H)
        self.log_text = tk.Text(self.log_frame, fg=C_TEXT, bg="#030e0e", insertbackground=C_TEXT, borderwidth=0, wrap="word", font=font_body(12), padx=12, pady=8)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        self.log_text.tag_config("you", foreground="#d0f0ee")
        self.log_text.tag_config("ai", foreground=C_PRI)
        self.log_text.tag_config("sys", foreground=C_GOLD)
        self.log_text.tag_config("err", foreground=C_RED)

        self._build_input_bar(self.CHAT_W)
        self._build_mute_button()
        self._build_pause_button()
        self._build_webcam_button()
        self._build_shutdown_button()
        self._build_social_bar()
        self._build_settings_panel()
        self._build_voice_selector(self._settings_body)
        self._build_sfx_button(self._settings_body)
        self._build_api_button(self._settings_body)
        self._build_fx_slider(self._settings_body)
        self._build_autostart_button(self._settings_body)
        self._build_shortcut_button(self._settings_body)
        self._layout_settings_controls()
        self._place_layout_widgets()
        self.bg.bind("<Button-1>", self._on_canvas_click)
        self.root.bind("<F4>", lambda e: self._toggle_mute())
        self.root.bind("<Control-m>", lambda e: self._toggle_mute())
        self.root.bind("<Escape>", lambda e: self._esc_action())
        self.root.bind("<F5>", lambda e: self._toggle_pause())
        self.root.bind("<F6>", lambda e: self._toggle_webcam_ui())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Control-f>", lambda e: self._toggle_fullscreen())

        self._api_key_ready = has_gemini_api_key()
        if not self._api_key_ready and not self._headless:
            self._show_setup_ui()

        self.root.bind("<Configure>", self._on_configure)
        self._effects_active = None
        self._sync_sound_state()
        if not self._headless:
            self._kick_brief_refresh()
            self.root.update_idletasks()
            self._draw()
            self.root.update()
            self._animate()
            self.root.deiconify()
            self.root.update()
            self._draw()
            self._fullscreen = True
            self._enter_fullscreen()
        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)
