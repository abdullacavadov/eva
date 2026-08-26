"""React dashboard üçün canlı EVA məlumatlarını toplayan HTTP adapteri."""

from __future__ import annotations

import re
from typing import Any

from actions.agenda import get_daily_agenda
from actions.email import search_emails
from actions.weather import get_weather_summary
from actions.sys_info import sys_info


def _percent_from_sys_info(text: str, prefix: str) -> float | None:
    for line in str(text or "").splitlines():
        if line.upper().startswith(prefix.upper()):
            match = re.search(r"%\s*([0-9]+(?:\.[0-9]+)?)", line)
            if match:
                return float(match.group(1))
    return None


def _battery_percent_from_sys_info(text: str) -> float | None:
    """sys_info('all') nəticəsindən batareya faizini çıxarır."""
    match = re.search(r"Pil:\s*%\s*([0-9]+(?:\.[0-9]+)?)", str(text or ""), re.IGNORECASE)
    return float(match.group(1)) if match else None


def _volume_percent() -> float | None:
    """Windows əsas səs çıxışının master volume faizini qaytarır."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        return round(float(volume.GetMasterVolumeLevelScalar()) * 100, 1)
    except Exception:
        return None


def _network_status(text: str) -> str:
    value = str(text or "").casefold()
    if "bağlı" in value or "ip " in value:
        return "ONLAYN"
    return "OFFLAYN"


def get_dashboard_data() -> dict[str, Any]:
    """Dashboard üçün bütün mənbələri real-time oxuyur; uğursuz mənbə digərlərini dayandırmır."""
    data: dict[str, Any] = {
        "ok": True,
        "overview": {
            "calendar_events": 0,
            "tasks_today": 0,
            "reminders": 0,
            "unread_messages": 0,
        },
        "weather": {"success": False},
        "system": {
            "cpu_percent": None,
            "memory_percent": None,
            "disk_percent": None,
            "network": None,
            "battery_percent": None,
            "volume_percent": None,
        },
        "context": {
            "source": "Google Calendar",
            "title": "Aktiv kontekst",
            "items": [],
        },
    }
    errors: dict[str, str] = {}

    try:
        agenda = get_daily_agenda(limit=100)
        groups = agenda.get("meta", {}).get("groups", {}) if isinstance(agenda, dict) else {}
        calendar_items = groups.get("calendar", []) if isinstance(groups, dict) else []
        task_items = groups.get("tasks", []) if isinstance(groups, dict) else []
        memory_items = groups.get("memory", []) if isinstance(groups, dict) else []
        data["overview"]["calendar_events"] = len(calendar_items)
        data["overview"]["tasks_today"] = len(task_items)
        data["overview"]["reminders"] = len(task_items) + len(memory_items)
        context_items = []
        for item in (calendar_items + task_items + memory_items)[:8]:
            if isinstance(item, dict):
                context_items.append({
                    "id": str(item.get("id", "")),
                    "title": str(item.get("title", item.get("summary", ""))),
                    "type": str(item.get("type", "item")),
                    "due": str(item.get("due", item.get("start", ""))),
                    "notes": str(item.get("notes", "")),
                    "completed": bool(item.get("completed", False)),
                    "source": str(item.get("source", "calendar")),
                })
        data["context"]["items"] = context_items
        if agenda.get("status") == "error":
            errors["agenda"] = str(agenda.get("meta", {}).get("message", "Agenda xətası"))
    except Exception as exc:
        errors["agenda"] = str(exc)

    try:
        weather = get_weather_summary()
        data["weather"] = weather
        if not weather.get("success"):
            errors["weather"] = "Hava məlumatı alınmadı."
    except Exception as exc:
        errors["weather"] = str(exc)

    try:
        system_text = sys_info("all")
        data["system"] = {
            "cpu_percent": _percent_from_sys_info(system_text, "CPU"),
            "memory_percent": _percent_from_sys_info(system_text, "RAM"),
            "disk_percent": None,
            "network": _network_status(system_text),
            "battery_percent": _battery_percent_from_sys_info(system_text),
            "volume_percent": _volume_percent(),
        }
        try:
            import psutil
            data["system"]["disk_percent"] = float(psutil.disk_usage("C:\\").percent)
        except Exception:
            pass
    except Exception as exc:
        errors["system"] = str(exc)

    try:
        unread = search_emails(query="is:unread", limit=1)
        if isinstance(unread, dict):
            data["overview"]["unread_messages"] = int(unread.get("count", unread.get("meta", {}).get("returned_count", 0)) or 0)
            if unread.get("status") == "error":
                errors["gmail"] = str(unread.get("meta", {}).get("message", "Gmail xətası"))
    except Exception as exc:
        errors["gmail"] = str(exc)

    data["errors"] = errors
    data["ok"] = not bool(errors) or any(
        value is not None for value in (
            data["weather"].get("temperature"),
            data["system"].get("cpu_percent"),
            data["overview"].get("calendar_events"),
        )
    )
    return data
