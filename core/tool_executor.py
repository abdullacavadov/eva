"""EVA alətlərinin icrası və nəticələrinin idarə olunması."""

import asyncio
import traceback
import re
from typing import Callable

from google.genai import types  # type: ignore[reportMissingImports]

from memory.memory_manager import (
    delete_memory,
    update_memory,
)
from actions.open_app import open_app
from actions.sys_info import sys_info
from actions.calendar import (
    get_calendar_events,
    add_calendar_event,
    delete_calendar_event,
)
from actions.reminders import get_reminders, add_reminder
from actions.browser import browser_control
from actions.shell import shell_run
from actions.whatsapp import send_whatsapp_message, save_whatsapp_contact
from actions.media import play_media
from actions.weather import get_weather_summary
from actions.screen_vision import analyze_screen
from actions.youtube_stats import get_youtube_channel_report


class ToolExecutor:
    """Gemini tərəfindən çağırılan EVA alətlərini icra edir."""

    CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

    def __init__(
        self,
        ui,
        webcam_streamer,
        focus_ui_section: Callable[[str, dict], None],
        speak_error: Callable[[str, str], None],
    ):
        self.ui = ui
        self.webcam_streamer = webcam_streamer
        self.focus_ui_section = focus_ui_section
        self.speak_error = speak_error

    @staticmethod
    def result_looks_like_error(result) -> bool:
        """Alət nəticəsinin xəta mesajına bənzəyib-bənzəmədiyini yoxlayır."""
        text = str(result or "").strip().lower()
        if not text:
            return False
        error_markers = (
            "hata",
            "error",
            "alinamadi",
            "alınamadı",
            "bulunamadi",
            "bulunamadı",
            "acilamadi",
            "açılamadı",
            "tamamlanamadi",
            "tamamlanamadı",
            "gecersiz",
            "geçersiz",
            "izin gerekiyor",
            "izin gerekli",
            "baglanti",
            "bağlantı",
            "gerekli.",
            "xəta",
            "mümkün olmadı",
        )
        return any(marker in text for marker in error_markers)

    @staticmethod
    def should_play_success_sfx(tool_name: str, args: dict, result) -> bool:
        """Uğurlu əməliyyatdan sonra səs effektinin çalınıb-çalınmayacağını müəyyən edir."""
        action_tools = {
            "open_app",
            "add_calendar_event",
            "add_reminder",
            "delete_calendar_event",
            "remove_calendar_event",
        }
        if tool_name in action_tools:
            return True

        if tool_name == "send_whatsapp_message":
            text = str(result or "").lower()
            if bool(args.get("send_now", False)):
                return "göndərildi" in text or "gonderildi" in text
            return False

        return False

    async def execute(self, fc) -> types.FunctionResponse:
        """Gemini function call-ını uyğun action-a yönləndirir."""
        name = fc.name
        args = dict(fc.args or {})
        print(f"[E.V.A] 🔧 {name} {args}")
        self.ui.set_state("THINKING")

        loop = asyncio.get_event_loop()
        result = "Tamam."
        had_exception = False

        try:
            if name == "save_memory":
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                    print(f"[Memory] 💾 {cat}/{key} = {val}")
                result = "ok"

            elif name == "delete_memory":
                result = delete_memory(
                    args.get("category", ""),
                    args.get("key", ""),
                    args.get("match_text", ""),
                )

            elif name == "open_app":
                r = await loop.run_in_executor(
                    None, lambda: open_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} açıldı."

            elif name == "sys_info":
                self.focus_ui_section(name, args)
                r = await loop.run_in_executor(
                    None, lambda: sys_info(args.get("query", "all")))
                result = r or "Məlumat alındı."

            elif name == "get_weather":
                self.focus_ui_section(name, args)
                r = await loop.run_in_executor(
                    None, lambda: get_weather_summary(args.get("location") or None))
                result = r or "Hava durumu məlumatı alındı."

            elif name == "get_calendar_events":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_calendar_events(
                        args.get("query", "today"),
                        int(args.get("limit", 6) or 6),
                    ),
                )
                result = r or "Təqvim məlumatı alındı."

            elif name == "add_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("end_iso", ""),
                        args.get("notes", ""),
                        args.get("location", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Təqvim tədbiri əlavə edildi."

            elif name == "delete_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: delete_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("delete_all_matches", False)),
                    ),
                )
                result = r or "Təqvim tədbiri silindi."

            elif name == "get_reminders":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_reminders(
                        args.get("query", "upcoming"),
                        int(args.get("limit", 8) or 8),
                        args.get("list_name", ""),
                    ),
                )
                result = r or "Xatırladıcı məlumatı alındı."

            elif name == "add_reminder":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_reminder(
                        args.get("title", ""),
                        args.get("due_iso", ""),
                        args.get("notes", ""),
                        args.get("list_name", ""),
                        args.get("priority", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Xatırladıcı əlavə edildi."

            elif name == "browser_control":
                r = await loop.run_in_executor(
                    None,
                    lambda: browser_control(
                        args.get("action"),
                        args.get("url"),
                        args.get("query"),
                    ),
                )
                result = r or "Tamam."

            elif name == "shell_run":
                r = await loop.run_in_executor(
                    None, lambda: shell_run(args.get("command", "")))
                result = r or "Əmr icra edildi."

            elif name == "toggle_webcam":
                action = str(args.get("action", "start")).strip().lower()
                if action == "start":
                    status = self.webcam_streamer.start()
                    if status == "ok":
                        self.ui.set_webcam_active(True)
                        result = (
                            "Webcam axını başladıldı. "
                            "Artıq kameranı görürəm — istədiyin vaxt sual verə bilərsən."
                        )
                    elif status == "already_active":
                        result = "Webcam artıq açıqdır, görüntünü alıram."
                    else:
                        result = "Webcam-i başlatmaq mümkün olmadı: opencv-python quraşdırılmayıb."
                else:
                    self.webcam_streamer.stop()
                    self.ui.set_webcam_active(False)
                    result = "Webcam axını dayandırıldı."

            elif name == "play_media":
                r = await loop.run_in_executor(
                    None,
                    lambda: play_media(
                        args.get("query", ""),
                        args.get("provider", "auto"),
                        bool(args.get("autoplay", True)),
                    ),
                )
                result = r or "Media oxudulmağa başladı."

            elif name == "get_youtube_channel_report":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_youtube_channel_report(
                        args.get("query", "overview"),
                        args.get("handle", ""),
                        int(args.get("video_limit", 6) or 6),
                    ),
                )
                result = r or "YouTube kanal hesabatı alındı."

            elif name == "analyze_screen":
                r = await loop.run_in_executor(
                    None,
                    lambda: analyze_screen(
                        args.get("query", "Ekranda nə var?"),
                        args.get("target", "active_window"),
                    ),
                )
                result = r or "Ekran analizi tamamlandı."

            elif name == "send_whatsapp_message":
                r = await loop.run_in_executor(
                    None,
                    lambda: send_whatsapp_message(
                        args.get("message", ""),
                        args.get("phone_number", ""),
                        args.get("recipient_name", ""),
                        bool(args.get("send_now", False)),
                        args.get("app_target", "auto"),
                    ),
                )
                result = r or "WhatsApp əməliyyatı tamamlandı."

            elif name == "save_whatsapp_contact":
                r = await loop.run_in_executor(
                    None,
                    lambda: save_whatsapp_contact(
                        args.get("display_name", ""),
                        args.get("phone_number", ""),
                        args.get("aliases", ""),
                    ),
                )
                result = r or "WhatsApp kontaktı yadda saxlanıldı."

            else:
                result = f"Naməlum alət: {name}"

        except Exception as e:
            result = f"Xəta: {e}"
            had_exception = True
            traceback.print_exc()
            self.speak_error(name, e)

        tool_failed = self.result_looks_like_error(result)
        if tool_failed:
            if not had_exception:
                self.ui.set_state("ERROR")
        elif self.should_play_success_sfx(name, args, result):
            self.ui.play_success_sfx()

        if not tool_failed and not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[E.V.A] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id,
            name=name,
            response={"result": result},
        )
