"""Calendar follow-up routing for conversational actions."""

from __future__ import annotations

from datetime import datetime, timedelta

from actions.calendar import delete_calendar_event_by_id, read_calendar_event, update_calendar_event_by_id
from core.result_resolver import FollowUpAction, ResultResolutionError


def build_calendar_follow_up(action: FollowUpAction) -> dict:
    item = action.item
    item_id = str(item.get("id", ""))
    if not item_id.startswith("calendar_event:"):
        raise ResultResolutionError("Calendar follow-up üçün calendar event tələb olunur")
    event_id = str(item.get("google_event_id", "")) or item_id.removeprefix("calendar_event:")
    if not event_id:
        raise ResultResolutionError("Calendar event identifikatoru tapılmadı")
    calendar_name = str(item.get("calendar_id", ""))

    if action.action == "show":
        return {"tool_name": "read_calendar_event", "args": {"event_id": event_id, "calendar_name": calendar_name}, "item": item}

    if action.action == "delete":
        return {"tool_name": "delete_calendar_event_by_id", "args": {"event_id": event_id, "calendar_name": calendar_name}, "item": item, "confirmation_required": True}

    if action.action != "update":
        raise ResultResolutionError("Calendar üçün dəstəklənməyən follow-up əməli")

    text = str(action.action_text or "").casefold()
    if "sabah" not in text:
        raise ResultResolutionError("Calendar yeniləməsi üçün hazırda yalnız 'sabaha keçir' dəstəklənir")
    start = str(item.get("start", ""))
    end = str(item.get("end", ""))
    if not start or not end:
        raise ResultResolutionError("Calendar event vaxt məlumatı tapılmadı")
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResultResolutionError("Calendar event vaxt formatı tanınmadı") from exc
    if start_dt.tzinfo is None:
        raise ResultResolutionError("Calendar event timezone məlumatı yoxdur")
    return {
        "tool_name": "update_calendar_event_by_id",
        "args": {
            "event_id": event_id,
            "calendar_name": calendar_name,
            "start_iso": (start_dt + timedelta(days=1)).isoformat(),
            "end_iso": (end_dt + timedelta(days=1)).isoformat(),
            "all_day": bool(item.get("all_day", False)),
        },
        "item": item,
    }


def execute_calendar_follow_up(dispatch: dict) -> dict:
    if dispatch.get("confirmation_required"):
        return {"status": "confirmation_required", **dispatch}
    tool = dispatch.get("tool_name")
    args = dict(dispatch.get("args", {}))
    if tool == "read_calendar_event":
        return read_calendar_event(**args)
    if tool == "update_calendar_event_by_id":
        return update_calendar_event_by_id(**args)
    if tool == "delete_calendar_event_by_id":
        raise ResultResolutionError("Calendar silmə üçün confirmation tələb olunur")
    raise ResultResolutionError("Calendar follow-up dispatch tanınmadı")
