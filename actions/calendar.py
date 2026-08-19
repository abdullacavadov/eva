"""
Google Calendar tool adapter.

Gemini tool interface bu modulde saxlanılır.
Real Google Calendar API çağırışları integrations.google.calendar
moduluna ötürülür.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from integrations.google.calendar import (
    create_event,
    delete_event,
    list_events,
    resolve_calendar_id,
)


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _parse_datetime(value: str) -> datetime:
    text = str(value or "").strip()

    if not text:
        raise ValueError("Tarix/saat boşdur.")

    normalized = text.replace("Z", "+00:00")

    try:
        result = datetime.fromisoformat(normalized)
    except ValueError:
        result = datetime.strptime(
            text,
            "%Y-%m-%d %H:%M",
        )

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=_local_now().tzinfo
        )

    return result


def _range_for_query(query: str):
    now = _local_now()
    today = now.date()

    normalized = str(query or "today").strip().lower()

    if normalized in {
        "today",
        "bu gün",
        "bugün",
        "bu gun",
    }:
        start = datetime.combine(
            today,
            time.min,
            tzinfo=now.tzinfo,
        )
        end = start + timedelta(days=1)
        return start, end

    if normalized in {
        "tomorrow",
        "sabah",
    }:
        start = datetime.combine(
            today + timedelta(days=1),
            time.min,
            tzinfo=now.tzinfo,
        )
        end = start + timedelta(days=1)
        return start, end

    if normalized in {
        "week",
        "agenda",
        "upcoming",
        "next",
        "həftə",
        "bu həftə",
        "bu hefte",
        "qarşıdakı",
        "yaxın",
    }:
        return now, now + timedelta(days=7)

    match = re.search(
        r"(\d+)\s*(gün|gun|days?)",
        normalized,
    )

    if match:
        days = int(match.group(1))
        return now, now + timedelta(days=days)

    match = re.search(
        r"(\d+)\s*(həftə|hefte|week|weeks)",
        normalized,
    )

    if match:
        weeks = int(match.group(1))
        return now, now + timedelta(days=weeks * 7)

    if "ay" in normalized or "month" in normalized:
        return now, now + timedelta(days=30)

    return now, now + timedelta(days=7)


def _format_event(event: dict) -> str:
    event_id = event.get("id", "")
    title = event.get("summary") or "(Adsız event)"

    start = event.get("start", {})

    if "dateTime" in start:
        start_value = start["dateTime"]
    else:
        start_value = start.get("date", "")

    location = event.get("location", "")
    description = event.get("description", "")

    result = f"- {title} — {start_value}"

    if location:
        result += f" — {location}"

    if description:
        result += f" — {description}"

    return result


def get_calendar_events(
    query: str = "today",
    limit: int = 6,
) -> str:
    try:
        start, end = _range_for_query(query)

        events = list_events(
            calendar_id="primary",
            max_results=max(1, min(int(limit or 6), 50)),
            time_min=start.isoformat(),
            time_max=end.isoformat(),
        )

        if not events:
            return "Göstərilən tarix aralığında calendar event tapılmadı."

        lines = [
            f"Google Calendar — {len(events)} event:"
        ]

        for event in events:
            lines.append(_format_event(event))

        return "\n".join(lines)

    except Exception as exc:
        return f"Google Calendar oxunarkən xəta baş verdi: {exc}"


def add_calendar_event(
    title: str,
    start_iso: str,
    end_iso: str = "",
    notes: str = "",
    location: str = "",
    calendar_name: str = "",
    all_day: bool = False,
) -> str:
    try:
        title = str(title or "").strip()

        if not title:
            return "Event başlığı boş ola bilməz."

        calendar_id = resolve_calendar_id(calendar_name)

        if all_day:
            start_date = _parse_datetime(start_iso).date()

            if end_iso:
                end_date = _parse_datetime(end_iso).date()
            else:
                end_date = start_date + timedelta(days=1)

            event = create_event(
                title=title,
                start_iso=start_date.isoformat(),
                end_iso=end_date.isoformat(),
                description=notes,
                location=location,
                calendar_id=calendar_id,
                all_day=True,
            )

        else:
            start = _parse_datetime(start_iso)

            if end_iso:
                end = _parse_datetime(end_iso)
            else:
                end = start + timedelta(hours=1)

            if end <= start:
                return "Event-in bitmə vaxtı başlanğıc vaxtından sonra olmalıdır."

            event = create_event(
                title=title,
                start_iso=start.isoformat(),
                end_iso=end.isoformat(),
                description=notes,
                location=location,
                calendar_id=calendar_id,
                all_day=False,
            )

        html_link = event.get("htmlLink", "")

        result = (
            f"Google Calendar-a '{title}' əlavə edildi."
        )

        if html_link:
            result += f" Link: {html_link}"

        return result

    except Exception as exc:
        return f"Google Calendar event yaradılarkən xəta baş verdi: {exc}"


def delete_calendar_event(
    title: str,
    start_iso: str = "",
    calendar_name: str = "",
    delete_all_matches: bool = False,
) -> str:
    try:
        title = str(title or "").strip()

        if not title:
            return "Silinəcək event başlığı göstərilməlidir."

        calendar_id = resolve_calendar_id(calendar_name)

        search_start = None
        search_end = None

        if start_iso:
            target = _parse_datetime(start_iso)

            # Event start-i exact axtarış üçün bir neçə dəqiqə
            # tolerantlıq saxlayırıq.
            search_start = (
                target - timedelta(minutes=2)
            ).isoformat()

            search_end = (
                target + timedelta(minutes=2)
            ).isoformat()
        else:
            search_start = _local_now().isoformat()
            search_end = (
                _local_now() + timedelta(days=365)
            ).isoformat()

        events = list_events(
            calendar_id=calendar_id,
            max_results=50,
            time_min=search_start,
            time_max=search_end,
            query=title,
        )

        exact_matches = [
            event
            for event in events
            if str(event.get("summary", "")).strip().casefold()
            == title.casefold()
        ]

        if start_iso:
            target = _parse_datetime(start_iso)

            def matches_start(event: dict) -> bool:
                start = event.get("start", {})

                if "dateTime" not in start:
                    return False

                try:
                    event_start = _parse_datetime(
                        start["dateTime"]
                    )
                except Exception:
                    return False

                return abs(
                    (event_start - target).total_seconds()
                ) <= 120

            exact_matches = [
                event
                for event in exact_matches
                if matches_start(event)
            ]

        if not exact_matches:
            return (
                f"'{title}' adlı uyğun event tapılmadı. "
                "Heç nə silinmədi."
            )

        if len(exact_matches) > 1 and not delete_all_matches:
            details = []

            for event in exact_matches[:10]:
                details.append(
                    _format_event(event)
                )

            return (
                f"'{title}' adlı {len(exact_matches)} event tapıldı. "
                "Təhlükəsizlik səbəbilə heç biri silinmədi. "
                "Dəqiq tarix/saat göstər və ya bütün uyğun event-ləri "
                "silmək üçün delete_all_matches=true tələb olunur.\n"
                + "\n".join(details)
            )

        deleted = 0

        targets = (
            exact_matches
            if delete_all_matches
            else exact_matches[:1]
        )

        for event in targets:
            event_id = event.get("id")

            if not event_id:
                continue

            delete_event(
                event_id=event_id,
                calendar_id=calendar_id,
            )

            deleted += 1

        if deleted == 1:
            return f"'{title}' adlı event silindi."

        return (
            f"'{title}' adlı {deleted} event silindi."
        )

    except Exception as exc:
        return f"Google Calendar event silinərkən xəta baş verdi: {exc}"