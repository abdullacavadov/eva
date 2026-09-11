#!/usr/bin/env python3
"""
EVA — Real vaxtda işləyən səsli köməkçinin əsas iş axını.
Windows mühitinə uyğunlaşdırılmış iş prosesi.
"""

import asyncio
import datetime
import threading
import traceback
import os
import re
import struct
from collections import deque

from google.genai import types  # type: ignore[reportMissingImports]

from app_config import get_app_config_value
from core.audio import (
    create_audio,
    open_input_stream,
    open_output_stream,
    read_chunk,
    write_chunk,
    interrupt_output_stream,
)
from core.config import (
    CHUNK_SIZE,
    CHANNELS,
    FORMAT,
    LIVE_MODEL,
    RECV_SAMPLE_RATE,
    SEND_SAMPLE_RATE,
    get_api_key,
    load_system_prompt,
)
from core.interruption import BargeInDetector
from core.live_session import LiveSessionManager
from core.proactive import ProactiveEngine, ProactiveScheduler
from core.tool_executor import ToolExecutor
from core.webcam import WebcamStreamer
from ui import JarvisUI
from memory.memory_manager import load_memory, format_memory_for_prompt

try:
    from wakeup_listener import WakeGestureListener
except Exception:
    WakeGestureListener = None

CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

from tool_defs import TOOL_DECLARATIONS


class JarvisLive:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._output_gain = 1.0
        self._output_gain_lock = threading.Lock()
        self._barge_in = BargeInDetector(
            threshold=float(os.getenv("EVA_BARGE_IN_THRESHOLD", "0.045")),
            confirm_ms=float(os.getenv("EVA_BARGE_IN_CONFIRM_MS", "260")),
            sample_rate=SEND_SAMPLE_RATE,
            candidate_hold_ms=float(os.getenv("EVA_BARGE_IN_CANDIDATE_HOLD_MS", "700")),
        )
        self._barge_in_buffer = deque(maxlen=6)
        self._music_proc = None
        self._webcam_streamer = WebcamStreamer()
        self._audio = create_audio()
        self._pending_text_commands: list[str] = []
        self._pending_text_lock = threading.Lock()
        self._greeting_sent = False
        self._tool_executor = ToolExecutor(
            ui=self.ui,
            webcam_streamer=self._webcam_streamer,
            focus_ui_section=self._focus_ui_section_for_tool,
            speak_error=self.speak_error,
        )

        self.ui.on_text_command = self._on_text_command
        self.ui.on_pause_toggle = self._on_pause_toggle
        self.ui.on_effects_state_change = self._on_effects_state_change
        self.ui.on_webcam_toggle = self._on_webcam_toggle_ui
        self._paused = False

    def _on_pause_toggle(self, paused: bool):
        self._paused = paused
        if paused:
            self._stop_music()

    def _on_effects_state_change(self, enabled: bool):
        if not enabled:
            self._stop_music()

    def _on_webcam_toggle_ui(self, activate: bool):
        if activate:
            status = self._webcam_streamer.start()
            self.ui.set_webcam_active(status == "ok" or status == "already_active")
        else:
            self._webcam_streamer.stop()
            self.ui.set_webcam_active(False)

    def _on_proactive_notification(self, event: dict) -> bool:
        text = str(event.get("text") or event.get("title") or "Proaktiv bildiriş").strip()
        if not text:
            return False
        try:
            self.ui.root.after(0, self._apply_proactive_notification, text)
            return True
        except Exception as exc:
            self.ui.write_debug(f"Proactive notification queue xətası: {exc}", level="ERROR")
            return False

    def _apply_proactive_notification(self, text: str):
        try:
            self.ui.write_log(f"E.V.A 🔔: {text}")
            self.ui.write_debug(f"Proactive: {text}", level="INFO")
        except Exception as exc:
            try:
                self.ui.write_debug(f"Proactive notification UI xətası: {exc}", level="ERROR")
            except Exception:
                pass

    def _focus_ui_section_for_tool(self, tool_name: str, args: dict):
        if tool_name == "sys_info":
            query = str(args.get("query", "")).strip().lower()
            if query in {"time", "saat", "zaman", "date", "tarih"}:
                self.ui.focus_panel("time", duration_ms=5200)
            else:
                self.ui.focus_panel("system", duration_ms=5200)
        elif tool_name == "get_weather":
            self.ui.focus_panel("weather", duration_ms=5600)

    def _on_text_command(self, text: str):
        if self._paused:
            return
        clean = str(text or "").strip()
        if not clean:
            return
        self.ui.write_log(f"Siz: {clean}")
        with self._pending_text_lock:
            if not self._loop or not self.session:
                self._pending_text_commands.append(clean)
                self.ui.write_log("SYS: Əmr növbəyə əlavə edildi; E.V.A bağlantısı hazır olan kimi icra olunacaq.")
                return
        self._send_text_to_session(clean)

    def _send_text_to_session(self, text: str) -> bool:
        loop = self._loop
        session = self.session
        if not loop or not session:
            return False
        try:
            future = asyncio.run_coroutine_threadsafe(
                session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True,
                ),
                loop,
            )
            future.add_done_callback(self._log_text_send_error)
            return True
        except Exception as exc:
            self.ui.write_log(f"ERR: Əmr göndərilə bilmədi — {exc}")
            return False

    def _log_text_send_error(self, future):
        try:
            future.result()
        except Exception as exc:
            self.ui.write_log(f"ERR: Əmr göndərilməsi uğursuz oldu — {exc}")

    async def _flush_pending_text_commands(self):
        with self._pending_text_lock:
            pending = self._pending_text_commands[:]
            self._pending_text_commands.clear()
        for text in pending:
            if self._send_text_to_session(text):
                await asyncio.sleep(0.05)
            else:
                with self._pending_text_lock:
                    self._pending_text_commands.insert(0, text)
                break

    def _set_output_gain(self, gain: float):
        with self._output_gain_lock:
            self._output_gain = max(0.0, min(1.0, float(gain)))

    def _get_output_gain(self) -> float:
        with self._output_gain_lock:
            return self._output_gain

    def _interrupt_audio(self):
        if self._loop and self.audio_in_queue:
            asyncio.run_coroutine_threadsafe(self._interrupt_audio_async(), self._loop)

    async def _interrupt_audio_async(self):
        try:
            interrupt_output_stream()
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            if self.out_queue:
                while not self.out_queue.empty():
                    try:
                        self.out_queue.get_nowait()
                    except Exception:
                        break
            self._set_output_gain(1.0)
            self._barge_in.reset()
            self.set_speaking(False)
        except Exception:
            pass

    def _stop_music(self):
        proc = self._music_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self._music_proc = None

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        else:
            self.ui.set_state("LISTENING")

    def _emit_audio_level(self, chunk: bytes):
        """Səsləndirilən PCM chunk üçün real amplitudanı React UI-a göndərir."""
        callback = getattr(self.ui, "emit_event", None)
        if not callable(callback) or not chunk:
            return
        try:
            sample_count = len(chunk) // 2
            if sample_count <= 0:
                return
            samples = struct.unpack(f"<{sample_count}h", chunk[:sample_count * 2])
            mean_square = sum(sample * sample for sample in samples) / sample_count
            rms = mean_square ** 0.5
            level = max(0.0, min(1.0, rms / 32768.0 * 3.0))
            callback("audio.level", level=level)
        except Exception:
            pass

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.ui.write_debug(f"{tool_name}: {short}", level="ERROR")
