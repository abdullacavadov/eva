"""Google Calendar tool adapter."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, time

from core.results import empty, error, success
from integrations.google.calendar import create_event, delete_event, list_events, resolve_calendar_id, update_event


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _parse_datetime(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Tarix/saat boşdur.")
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        result = datetime.strptime(text, "%Y-%m-%d %H:%M")
    if result.tzinfo is None:
        result = result.replace(tzinfo=_local_now().tzinfo)
    return result


def _range_for_query(query: str):
    now = _local_now()
    today = now.date()
    normalized = str(query or "today").strip().lower()
    if normalized in {"today", "bu gün", "bugün", "bu gun"}:
        start = datetime.combine(today, time.min, tzinfo=now.tzinfo)
        return start, start + timedelta(days=1)
    if normalized in {"tomorrow", "sabah"}:
        start = datetime.combine(today + timedelta(days=1), time.min, tzinfo=now.tzinfo)
        return start, start + timedelta(days=1)
    if normalized in {"week", "agenda", "upcoming", "next", "həftə", "bu həftə", "bu hefte", "qarşıdakı", "yaxın"}:
        return now, now + timedelta(days=7)
    match = re.search(r"(\d+)\s*(gün|gun|days?)", normalized)
    if match:
        return now, now + timedelta(days=int(match.group(1)))
    match = re.search(r"(\d+)\s*(həftə|hefte|week|weeks)", normalized)
    if match:
        return now, now + timedelta(days=int(match.group(1)) * 7)
    if "ay" in normalized or "month" in normalized:
        return now, now + timedelta(days=30)
    return now, now + timedelta(days=7)


def _structured_event(event: dict, calendar_id: str = "primary") -> dict:
    start = event.get("start", {}) or {}
    end = event.get("end", {}) or {}
    return {
        "id": f"calendar_event:{event.get('id', '')}",
        "google_event_id": event.get("id", ""),
        "calendar_id": calendar_id,
        "title": event.get("summary") or "(Adsız event)",
        "start": start.get("dateTime") or start.get("date", ""),
        "end": end.get("dateTime") or end.get("date", ""),
        "all_day": "date" in start and "dateTime" not in start,
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "html_link": event.get("htmlLink", ""),
        "status": event.get("status", ""),
    }


def get_calendar_events(query: str = "today", limit: int = 6) -> dict:
    try:
        start, end = _range_for_query(query)
        result_limit = max(1, min(int(limit or 6), 50))
        events = list_events(calendar_id="primary", max_results=result_limit, time_min=start.isoformat(), time_max=end.isoformat())
        payload = {"query": query, "limit": result_limit, "time_min": start.isoformat(), "time_max": end.isoformat()}
        if not events:
            return empty("calendar_event", payload)
        return success("calendar_event", [_structured_event(event) for event in events], payload)
    except Exception as exc:
        return error("calendar_event", str(exc), {"query": query, "limit": limit})


def read_calendar_event(event_id: str, calendar_name: str = "") -> dict:
    try:
        calendar_id = resolve_calendar_id(calendar_name)
        events = list_events(calendar_id=calendar_id, max_results=50, query=str(event_id or ""))
        exact = [event for event in events if str(event.get("id", "")) == str(event_id)]
        if not exact:
            return empty("calendar_event", {"event_id": event_id, "calendar_name": calendar_name})
        item = _structured_event(exact[0], calendar_id)
        return success("calendar_event", [item], {"event_id": event_id, "calendar_name": calendar_name}, {"selected_id": item["id"]})
    except Exception as exc:
        return error("calendar_event", str(exc), {"event_id": event_id})


def update_calendar_event_by_id(event_id: str, calendar_name: str = "", title: str | None = None, start_iso: str = "", end_iso: str = "", notes: str | None = None, location: str | None = None, all_day: bool | None = None) -> dict:
    try:
        calendar_id = resolve_calendar_id(calendar_name)
        event = update_event(event_id=event_id, calendar_id=calendar_id, title=title, start_iso=start_iso, end_iso=end_iso, notes=notes, location=location, all_day=all_day)
        item = _structured_event(event, calendar_id)
        return success("calendar_event", [item], {"event_id": event_id, "calendar_name": calendar_name}, {"selected_id": item["id"]})
    except Exception as exc:
        return error("calendar_event", str(exc), {"event_id": event_id})


def delete_calendar_event_by_id(event_id: str, calendar_name: str = "") -> dict:
    try:
        calendar_id = resolve_calendar_id(calendar_name)
        delete_event(event_id=event_id, calendar_id=calendar_id)
        return success("calendar_event", [{"id": f"calendar_event:{event_id}", "google_event_id": event_id, "action": "delete", "status": "deleted"}], {"event_id": event_id, "calendar_name": calendar_name})
    except Exception as exc:
        return error("calendar_event", str(exc), {"event_id": event_id})


def add_calendar_event(title: str, start_iso: str, end_iso: str = "", notes: str = "", location: str = "", calendar_name: str = "", all_day: bool = False) -> dict:
    try:
        title = str(title or "").strip()
        if not title:
            return error("calendar_event", "Event başlığı boş ola bilməz.")
        calendar_id = resolve_calendar_id(calendar_name)
        if all_day:
            start_date = _parse_datetime(start_iso).date()
            end_date = _parse_datetime(end_iso).date() if end_iso else start_date + timedelta(days=1)
            event = create_event(title=title, start_iso=start_date.isoformat(), end_iso=end_date.isoformat(), description=notes, location=location, calendar_id=calendar_id, all_day=True)
        else:
            start = _parse_datetime(start_iso)
            end = _parse_datetime(end_iso) if end_iso else start + timedelta(hours=1)
            if end <= start:
                return error("calendar_event", "Event-in bitmə vaxtı başlanğıc vaxtından sonra olmalıdır.")
            event = create_event(title=title, start_iso=start.isoformat(), end_iso=end.isoformat(), description=notes, location=location, calendar_id=calendar_id, all_day=False)
        item = _structured_event(event, calendar_id)
        return success("calendar_event", [item], {"calendar_name": calendar_name, "calendar_id": calendar_id}, {"selected_id": item["id"]})
    except Exception as exc:
        return error("calendar_event", str(exc))


def delete_calendar_event(title: str, start_iso: str = "", calendar_name: str = "", delete_all_matches: bool = False) -> dict:
    try:
        title = str(title or "").strip()
        if not title:
            return error("calendar_event", "Silinəcək event başlığı göstərilməlidir.")
        calendar_id = resolve_calendar_id(calendar_name)
        if start_iso:
            target = _parse_datetime(start_iso)
            search_start = (target - timedelta(minutes=2)).isoformat()
            search_end = (target + timedelta(minutes=2)).isoformat()
        else:
            search_start = _local_now().isoformat()
            search_end = (_local_now() + timedelta(days=365)).isoformat()
        events = list_events(calendar_id=calendar_id, max_results=50, time_min=search_start, time_max=search_end, query=title)
        exact_matches = [e for e in events if str(e.get("summary", "")).strip().casefold() == title.casefold()]
        if start_iso:
            target = _parse_datetime(start_iso)
            exact_matches = [e for e in exact_matches if "dateTime" in e.get("start", {}) and abs((_parse_datetime(e["start"]["dateTime"]) - target).total_seconds()) <= 120]
        payload = {"title": title, "start_iso": start_iso, "calendar_name": calendar_name, "delete_all_matches": delete_all_matches}
        if not exact_matches:
            return empty("calendar_event", payload)
        if len(exact_matches) > 1 and not delete_all_matches:
            return {**success("calendar_event", [_structured_event(event, calendar_id) for event in exact_matches[:10]], payload), "status": "partial", "meta": {"message": "Bir neçə uyğun event tapıldı; təhlükəsizlik səbəbilə heç biri silinmədi."}}
        targets = exact_matches if delete_all_matches else exact_matches[:1]
        deleted = []
        for event in targets:
            event_id = event.get("id")
            if event_id:
                delete_event(event_id=event_id, calendar_id=calendar_id)
                deleted.append(_structured_event(event, calendar_id))
        return success("calendar_event", deleted, payload)
    except Exception as exc:
        return error("calendar_event", str(exc), {"title": title, "start_iso": start_iso})
