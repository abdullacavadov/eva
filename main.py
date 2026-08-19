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

from google.genai import types  # type: ignore[reportMissingImports]

from app_config import get_app_config_value
from core.audio import (
    create_audio,
    open_input_stream,
    open_output_stream,
    read_chunk,
    write_chunk,
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
from core.live_session import LiveSessionManager
from core.tool_executor import ToolExecutor
from core.webcam import WebcamStreamer
from ui import JarvisUI
from memory.memory_manager import load_memory, format_memory_for_prompt

try:
    from wakeup_listener import WakeGestureListener
except Exception:
    # Mikrofon əlçatan olmasa belə tətbiqin açılmasına imkan ver.
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
        self._music_proc = None
        self._webcam_streamer = WebcamStreamer()
        self._audio = create_audio()
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
        self.ui.write_log(f"Siz: {text}")
        if not self._loop or not self.session:
            self.ui.write_log("ERR: E.V.A bağlantısı hələ hazır deyil.")
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True,
            ),
            self._loop,
        )

    async def _interrupt_audio(self):
        try:
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            if self.session:
                await self.session.send_realtime_input(audio_stream_end=True)
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

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.ui.write_debug(f"{tool_name}: {short}", level="ERROR")
        self.ui.set_state("ERROR")

    @staticmethod
    def _clean_transcript_text(text: str) -> tuple[str, bool]:
        raw = str(text or "")
        had_noise = False
        if CONTROL_TOKEN_RE.search(raw):
            had_noise = True
            raw = CONTROL_TOKEN_RE.sub(" ", raw)
        cleaned = []
        for ch in raw:
            if ch in "\n\r\t" or ord(ch) >= 32:
                cleaned.append(ch)
            else:
                had_noise = True
        normalized = " ".join("".join(cleaned).split())
        return normalized.strip(), had_noise

    def _build_config(self) -> types.LiveConnectConfig:
        memory = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_p = load_system_prompt()
        now = datetime.datetime.now()
        time_ctx = f"[ŞU ANKİ ZAMAN]\n{now.strftime('%A, %d %B %Y — %H:%M')}\n\n"

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str + "\n\n")
        parts.append(sys_p)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=str(get_app_config_value("voice", "Charon") or "Charon")
                    )
                )
            ),
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _stream_webcam_frames(self):
        """Webcam aktivdirsə ən son kadrı təxminən hər 1,5 saniyədə sessiyaya göndərir."""
        _last_sent: bytes | None = None
        while True:
            if not self._webcam_streamer.is_active:
                await asyncio.sleep(0.2)
                continue

            jpeg = self._webcam_streamer.get_latest_frame()
            if jpeg is None or jpeg is _last_sent:
                await asyncio.sleep(0.2)
                continue

            _last_sent = jpeg
            try:
                await self.session.send_realtime_input(
                    media={"data": jpeg, "mime_type": "image/jpeg"}
                )
            except Exception as e:
                print(f"[Webcam] Kadr göndərilə bilmədi: {e}")

            await asyncio.sleep(1.5)

    async def _update_ui_webcam_preview(self):
        """UI önizləməsini təxminən 24 FPS sürətlə yeniləyir."""
        frame_interval = 1.0 / 24.0
        while True:
            if self._webcam_streamer.is_active:
                jpeg = self._webcam_streamer.get_latest_frame()
                if jpeg:
                    self.ui.update_webcam_preview(jpeg)
            await asyncio.sleep(frame_interval)

    async def _listen_audio(self):
        print("[E.V.A] 🎤 Mikrofon başladı")
        stream = await open_input_stream(self._audio)
        try:
            while True:
                data = await read_chunk(stream, CHUNK_SIZE)
                with self._speaking_lock:
                    jarvis_speaking = self._is_speaking
                if not jarvis_speaking and not self.ui.muted and not self._paused:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
        except Exception as e:
            print(f"[E.V.A] ❌ Mikrofon: {e}")
            raise
        finally:
            stream.close()

    async def _receive_audio(self):
        print("[E.V.A] 👂 Səs qəbulu başladı")
        out_buf, in_buf = [], []
        output_noise = False
        output_noise_samples = []
        try:
            while True:
                async for response in self.session.receive():
                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            raw_txt = sc.output_transcription.text.strip()
                            if raw_txt:
                                txt, had_noise = self._clean_transcript_text(raw_txt)
                                if had_noise:
                                    output_noise = True
                                    if len(output_noise_samples) < 4:
                                        output_noise_samples.append(raw_txt)
                                if txt:
                                    out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                                self.ui.mark_user_activity(True)

                        if sc.turn_complete:
                            self.audio_in_queue.put_nowait(None)

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"Siz: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"E.V.A: {full_out}")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Qismən süzülmüş səs transkripti: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                            elif output_noise:
                                self.ui.write_log("ERR: E.V.A səsli cavabını emal edərkən xəta baş verdi.")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Süzülmüş xam transkript: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                                self.ui.set_state("ERROR")
                            out_buf = []
                            output_noise = False
                            output_noise_samples = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[E.V.A] 📞 {fc.name}")
                            fr = await self._tool_executor.execute(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[E.V.A] ❌ Səs qəbulu: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[E.V.A] 🔊 Səs səsləndirməsi başladı")
        stream = await open_output_stream(self._audio)
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                if chunk is None:
                    self.set_speaking(False)
                    continue
                self.set_speaking(True)
                await write_chunk(stream, chunk)
        except Exception as e:
            print(f"[E.V.A] ❌ Səs: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.close()

    async def run(self):
        connect_attempts = 0
        while True:
            if self._paused:
                await asyncio.sleep(1)
                continue

            try:
                session_manager = LiveSessionManager(LIVE_MODEL, get_api_key())
                print("[E.V.A] 🔌 Qoşulur...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    session_manager.connect(config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session
                    self._loop = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)

                    print("[E.V.A] ✅ Bağlandı.")
                    connect_attempts = 0
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: E.V.A hazırdır. Eşidirəm...")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._stream_webcam_frames())
                    tg.create_task(self._update_ui_webcam_preview())

            except Exception as e:
                print(f"[E.V.A] ⚠️ {e}")
                traceback.print_exc()
                self.set_speaking(False)
                if self._webcam_streamer.is_active:
                    self._webcam_streamer.stop()
                    self.ui.set_webcam_active(False)

                connect_attempts += 1
                if connect_attempts <= 3:
                    self.ui.set_state("INITIALISING")
                    print(f"[E.V.A] 🔄 Yenidən qoşulmağa cəhd edir ({connect_attempts}/3)...")
                    await asyncio.sleep(2)
                else:
                    self.ui.write_log(
                        f"ERR: E.V.A qoşula bilmir — API açarını və internet "
                        f"bağlantısını yoxla. ({e})"
                    )
                    self.ui.set_state("ERROR")
                    print("[E.V.A] 🔄 5 saniyə ərzində yenidən qoşulacaq...")
                    await asyncio.sleep(5)


def main():
    if os.environ.get("TERM_PROGRAM") == "vscode":
        print("[E.V.A] VS Code daxilində başladıldı.")

    ui = JarvisUI()

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Ayrılır...")

    threading.Thread(target=runner, daemon=True).start()

    ENABLE_CLAP_WAKE = False
    if ENABLE_CLAP_WAKE and WakeGestureListener is not None:
        try:
            wake_listener = WakeGestureListener(on_wake=ui.wake_up)
            wake_listener.start()
        except Exception as exc:
            print(f"[Wake] Alqış dinləyicisi başlamadı: {exc}")

    ui.root.mainloop()


if __name__ == "__main__":
    main()
