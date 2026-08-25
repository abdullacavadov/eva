"""EVA alətlərinin icrası və nəticələrinin idarə olunması."""

import asyncio
import traceback
import re
from dataclasses import dataclass
from typing import Callable

from google.genai import types  # type: ignore[reportMissingImports]

from memory.memory_manager import delete_memory, update_memory
from actions.open_app import open_app
from actions.sys_info import sys_info
from actions.calendar import get_calendar_events, add_calendar_event, delete_calendar_event
from actions.reminders import get_reminders, add_reminder, update_reminder, complete_reminder, delete_reminder
from actions.agenda import get_daily_agenda, add_agenda_item, delete_agenda_item
from actions.email import delete_email, prepare_email_deletion, prepare_email_reply, prepare_new_email, prepare_trash_emails, read_email_thread, search_emails, read_email, send_email, trash_emails
from actions.browser import browser_control
from actions.shell import shell_run
from actions.whatsapp import send_whatsapp_message, save_whatsapp_contact
from actions.whatsapp_read_action import read_whatsapp_conversations, read_whatsapp_messages
from actions.contacts import create_contact, delete_contact, sync_google_contacts, update_contact
from actions.media import play_media
from actions.weather import get_weather_summary
from actions.screen_vision import analyze_screen
from actions.youtube_stats import get_youtube_channel_report
from core.result_store import ResultStore
from core.result_resolver import FollowUpAction, ResultResolutionError, resolve_item, resolve_reference
from core.follow_up_mutation import build_follow_up_mutation
from core.orchestrator import execute_unified_query

import tool_defs as _tool_defs
from core.contact_tool_defs import CONTACT_TOOL_DECLARATIONS
from core.email_tool_defs import EMAIL_TOOL_DECLARATIONS
from core.whatsapp_tool_defs import WHATSAPP_TOOL_DECLARATIONS
from core.task_tool_defs import TASK_TOOL_DECLARATIONS

for _declaration in [*EMAIL_TOOL_DECLARATIONS, *CONTACT_TOOL_DECLARATIONS, *WHATSAPP_TOOL_DECLARATIONS, *TASK_TOOL_DECLARATIONS]:
    if not any(item.get("name") == _declaration["name"] for item in _tool_defs.TOOL_DECLARATIONS):
        _tool_defs.TOOL_DECLARATIONS.append(_declaration)


@dataclass(frozen=True)
class FollowUpDispatch:
    """Həll edilmiş follow-up üçün icra ediləcək alət və arqumentləri təsvir edir."""

    tool_name: str | None
    args: dict
    item: dict
    confirmation_required: bool = False


def _task_identity(item: dict) -> tuple[str, str]:
    item_id = str(item.get("id", ""))
    if not item_id.startswith("task:"):
        raise ResultResolutionError("Follow-up əməli üçün dəstəklənməyən entity")
    task_id = str(item.get("google_task_id", "")) or item_id.removeprefix("task:")
    list_name = str(item.get("task_list_id", ""))
    if not task_id:
        raise ResultResolutionError("Follow-up task identifikatoru tapılmadı")
    return task_id, list_name


def build_follow_up_dispatch(action: FollowUpAction) -> FollowUpDispatch:
    """FollowUpAction-ı təhlükəsiz tool dispatch planına çevirir."""
    item = action.item
    if action.action == "show":
        return FollowUpDispatch(None, {}, item)
    if action.action == "complete":
        task_id, list_name = _task_identity(item)
        return FollowUpDispatch("complete_reminder", {"task_id": task_id, "list_name": list_name}, item)
    if action.action == "delete":
        task_id, list_name = _task_identity(item)
        return FollowUpDispatch("delete_reminder", {"task_id": task_id, "list_name": list_name}, item, True)
    if action.action == "update":
        task_id, list_name = _task_identity(item)
        mutation = build_follow_up_mutation(action)
        return FollowUpDispatch("update_reminder", {"task_id": task_id, "list_name": list_name, **mutation.fields}, item)
    raise ResultResolutionError("Follow-up üçün dəstəklənməyən əməl")


class ToolExecutor:
    """Gemini tərəfindən çağırılan EVA alətlərini icra edir."""

    CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

    def __init__(self, ui, webcam_streamer, focus_ui_section: Callable[[str, dict], None], speak_error: Callable[[str, str], None], result_store: ResultStore | None = None):
        self.ui = ui
        self.webcam_streamer = webcam_streamer
        self.focus_ui_section = focus_ui_section
        self.speak_error = speak_error
        self.result_store = result_store or ResultStore()

    def resolve_follow_up(self, query: str) -> dict:
        context = self.result_store.current()
        if context is None:
            raise ResultResolutionError("Əvvəlki nəticə tapılmadı")
        selected = self.result_store.selected(context.result_id)
        item = resolve_reference(context, query, selected_item=selected)
        self.result_store.select(context.result_id, item["id"])
        return item

    @staticmethod
    def result_looks_like_error(result) -> bool:
        text = str(result or "").strip().lower()
        if not text:
            return False
        return any(marker in text for marker in ("hata", "error", "xəta", "alinamadi", "alınamadı", "bulunamadi", "bulunamadı", "acilamadi", "açılamadı", "tamamlanamadi", "tamamlanamadı", "gecersiz", "geçərsiz", "izin gerekiyor", "izin gerekli", "baglanti", "bağlantı", "gerekli.", "mümkün olmadı"))

    @staticmethod
    def should_play_success_sfx(tool_name: str, args: dict, result) -> bool:
        action_tools = {"open_app", "add_calendar_event", "add_reminder", "update_reminder", "complete_reminder", "delete_reminder", "add_agenda_item", "delete_agenda_item", "create_contact", "update_contact", "delete_contact", "trash_emails", "delete_email", "delete_calendar_event", "remove_calendar_event"}
        if tool_name in action_tools:
            return True
        if tool_name == "send_whatsapp_message":
            text = str(result or "").lower()
            return bool(args.get("send_now", False)) and ("göndərildi" in text or "gonderildi" in text)
        return False

    async def execute(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})
        print(f"[E.V.A] 🔧 {name} {args}")
        self.ui.set_state("THINKING")
        loop = asyncio.get_event_loop()
        result = "Tamam."
        had_exception = False
        try:
            if name == "save_memory":
                cat, key, val = args.get("category", "notes"), args.get("key", ""), args.get("value", "")
                if not key or not val: result = "Yaddaşı saxlamaq üçün key və value tələb olunur."
                else: update_memory({cat: {key: {"value": val}}}); print(f"[Memory] 💾 {cat}/{key} = {val}"); result = "ok"
            elif name == "delete_memory": result = delete_memory(args.get("category", ""), args.get("key", ""), args.get("match_text", ""))
            elif name == "get_calendar_events": result = await loop.run_in_executor(None, lambda: get_calendar_events(args.get("query", "today"), int(args.get("limit", 6) or 6))) or "Təqvim məlumatı alındı."
            elif name == "add_calendar_event": result = await loop.run_in_executor(None, lambda: add_calendar_event(args.get("title", ""), args.get("start_iso", ""), args.get("end_iso", ""), args.get("notes", ""), args.get("location", ""), args.get("calendar_name", ""), bool(args.get("all_day", False)))) or "Təqvim tədbiri əlavə edildi."
            elif name == "delete_calendar_event": result = await loop.run_in_executor(None, lambda: delete_calendar_event(args.get("title", ""), args.get("start_iso", ""), args.get("calendar_name", ""), bool(args.get("delete_all_matches", False)))) or "Təqvim tədbiri silindi."
            elif name == "get_reminders": result = await loop.run_in_executor(None, lambda: get_reminders(args.get("query", "upcoming"), int(args.get("limit", 8) or 8), args.get("list_name", ""))) or "Task məlumatı alındı."
            elif name == "add_reminder": result = await loop.run_in_executor(None, lambda: add_reminder(args.get("title", ""), args.get("due_iso", ""), args.get("notes", ""), args.get("list_name", ""), args.get("priority", ""), bool(args.get("all_day", False)))) or "Task əlavə edildi."
            elif name == "update_reminder": result = await loop.run_in_executor(None, lambda: update_reminder(args.get("task_id", ""), args.get("title", ""), args.get("due_iso", ""), args.get("notes", ""), args.get("list_name", ""), bool(args.get("all_day", False)))) or "Task yeniləndi."
            elif name == "complete_reminder": result = await loop.run_in_executor(None, lambda: complete_reminder(args.get("task_id", ""), args.get("list_name", ""))) or "Task tamamlandı."
            elif name == "delete_reminder": result = await loop.run_in_executor(None, lambda: delete_reminder(args.get("task_id", ""), args.get("list_name", ""))) or "Task silindi."
            elif name == "get_daily_agenda": result = await loop.run_in_executor(None, lambda: get_daily_agenda(int(args.get("limit", 20) or 20))) or "Bu gün üçün agenda alındı."
            elif name == "add_agenda_item": result = await loop.run_in_executor(None, lambda: add_agenda_item(args.get("title", ""), args.get("item_type", "task"), args.get("storage", ""), args.get("due_iso", ""), args.get("notes", ""))) or "Agenda elementi əlavə edildi."
            elif name == "delete_agenda_item": result = await loop.run_in_executor(None, lambda: delete_agenda_item(args.get("match_text", ""), args.get("storage", ""), bool(args.get("confirm", False)))) or "Agenda elementi silindi."
            elif name == "query_unified_assistant": result = await loop.run_in_executor(None, lambda: execute_unified_query(args.get("query", ""), int(args.get("limit", 8) or 8))) or "Unified sorğu icra edildi."
            elif name == "open_app": result = await loop.run_in_executor(None, lambda: open_app(args.get("app_name", ""))) or f"{args.get('app_name')} açıldı."
            elif name == "sys_info": self.focus_ui_section(name, args); result = await loop.run_in_executor(None, lambda: sys_info(args.get("query", "all"))) or "Məlumat alındı."
            elif name == "get_weather": self.focus_ui_section(name, args); result = await loop.run_in_executor(None, lambda: get_weather_summary(args.get("location") or None)) or "Hava durumu məlumatı alındı."
            elif name == "get_emails":
                q, lim, folder = args.get("query", ""), int(args.get("limit", 10) or 10), args.get("folder", "")
                result = await loop.run_in_executor(None, lambda: search_emails(q, lim, folder) if folder else search_emails(q, lim)) or "Email məlumatı alındı."
            elif name == "prepare_trash_emails": result = await loop.run_in_executor(None, lambda: prepare_trash_emails(args.get("folder", ""), args.get("message_id", ""), args.get("query", ""))) or "Email silmə planı hazırlandı."
            elif name == "trash_emails": result = await loop.run_in_executor(None, lambda: trash_emails(args.get("confirmation_id", ""))) or "Email(lər) Trash-a göndərildi."
            elif name == "prepare_email_deletion": result = await loop.run_in_executor(None, lambda: prepare_email_deletion(args.get("scope", ""), args.get("draft_id", ""))) or "Email silmə planı hazırlandı."
            elif name == "delete_email": result = await loop.run_in_executor(None, lambda: delete_email(args.get("confirmation_id", ""))) or "Email(lər) həmişəlik silindi."
            elif name == "read_email": result = await loop.run_in_executor(None, lambda: read_email(args.get("message_id", ""))) or "Email oxundu."
            elif name == "read_email_thread": result = await loop.run_in_executor(None, lambda: read_email_thread(args.get("thread_id", ""))) or "Email thread oxundu."
            elif name == "prepare_email_reply": result = await loop.run_in_executor(None, lambda: prepare_email_reply(args.get("message_id", ""), args.get("body", ""))) or "Email cavabı draft kimi hazırlandı."
            elif name == "prepare_new_email": result = await loop.run_in_executor(None, lambda: prepare_new_email(args.get("to", ""), args.get("subject", ""), args.get("body", ""), args.get("cc", ""), args.get("bcc", ""))) or "Yeni email draft kimi hazırlandı."
            elif name == "send_email": result = await loop.run_in_executor(None, lambda: send_email(args.get("draft_id", ""))) or "Email göndərildi."
            elif name == "sync_google_contacts": result = await loop.run_in_executor(None, sync_google_contacts) or "Google Contacts sinxronizasiyası tamamlandı."
            elif name == "create_contact": result = await loop.run_in_executor(None, lambda: create_contact(args.get("display_name", ""), args.get("phone_number", ""))) or "Google kontaktı yaradıldı."
            elif name == "update_contact": result = await loop.run_in_executor(None, lambda: update_contact(args.get("resource_name", ""), args.get("display_name", ""), args.get("phone_number", ""))) or "Google kontaktı yeniləndi."
            elif name == "delete_contact": result = await loop.run_in_executor(None, lambda: delete_contact(args.get("resource_name", ""))) or "Google kontaktı silindi."
            elif name == "browser_control": result = await loop.run_in_executor(None, lambda: browser_control(args.get("action"), args.get("url"), args.get("query"))) or "Tamam."
            elif name == "shell_run": result = await loop.run_in_executor(None, lambda: shell_run(args.get("command", ""))) or "Əmr icra edildi."
            elif name == "play_media": result = await loop.run_in_executor(None, lambda: play_media(args.get("query", ""), args.get("provider", "auto"), bool(args.get("autoplay", True)))) or "Media oxudulmağa başladı."
            elif name == "get_youtube_channel_report": result = await loop.run_in_executor(None, lambda: get_youtube_channel_report(args.get("query", "overview"), args.get("handle", ""), int(args.get("video_limit", 6) or 6))) or "YouTube kanal hesabatı alındı."
            elif name == "analyze_screen": result = await loop.run_in_executor(None, lambda: analyze_screen(args.get("query", "Ekranda nə var?"), args.get("target", "active_window"))) or "Ekran analizi tamamlandı."
            elif name == "send_whatsapp_message": result = await loop.run_in_executor(None, lambda: send_whatsapp_message(args.get("message", ""), args.get("phone_number", ""), args.get("recipient_name", ""), bool(args.get("send_now", False)), args.get("app_target", "auto"))) or "WhatsApp əməliyyatı tamamlandı."
            elif name == "save_whatsapp_contact": result = await loop.run_in_executor(None, lambda: save_whatsapp_contact(args.get("display_name", ""), args.get("phone_number", ""), args.get("aliases", ""))) or "WhatsApp kontaktı yadda saxlanıldı."
            elif name == "read_whatsapp_conversations": result = await loop.run_in_executor(None, read_whatsapp_conversations) or "WhatsApp söhbətləri oxundu."
            elif name == "read_whatsapp_messages": result = await loop.run_in_executor(None, lambda: read_whatsapp_messages(args.get("conversation", ""))) or "WhatsApp mesajları oxundu."
            elif name == "toggle_webcam":
                action = str(args.get("action", "start")).strip().lower()
                if action == "start":
                    status = self.webcam_streamer.start()
                    if status == "ok":
                        self.ui.set_webcam_active(True); result = "Webcam axını başladıldı. Artıq kameranı görürəm — istədiyin vaxt sual verə bilərsən."
                    elif status == "already_active": result = "Webcam artıq açıqdır, görüntünü alıram."
                    else: result = "Webcam-i başlatmaq mümkün olmadı: opencv-python quraşdırılmayıb."
                else:
                    self.webcam_streamer.stop(); self.ui.set_webcam_active(False); result = "Webcam axını dayandırıldı."
            else: result = f"Naməlum alət: {name}"
        except Exception as e:
            result = f"Xəta: {e}"; had_exception = True; traceback.print_exc(); self.speak_error(name, e); self.ui.set_state("ERROR")

        tool_failed = self.result_looks_like_error(result)
        if tool_failed:
            if not had_exception: self.ui.set_state("ERROR")
        elif self.should_play_success_sfx(name, args, result): self.ui.play_success_sfx()
        if isinstance(result, dict) and "type" in result and "status" in result and "data" in result: self.result_store.save(result)
        if not tool_failed and not self.ui.muted: self.ui.set_state("LISTENING")
        print(f"[E.V.A] 📤 {name} → {str(result)[:80]}...")
        return types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result})
