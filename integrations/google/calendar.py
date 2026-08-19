from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build

from integrations.google.auth import get_calendar_credentials


def get_calendar_service():
    return build(
        "calendar",
        "v3",
        credentials=get_calendar_credentials(),
    )


def list_calendars() -> list[dict[str, Any]]:
    service = get_calendar_service()

    calendars: list[dict[str, Any]] = []
    page_token = None

    while True:
        result = (
            service.calendarList()
            .list(
                pageToken=page_token,
                minAccessRole="reader",
            )
            .execute()
        )

        calendars.extend(result.get("items", []))

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return calendars


def resolve_calendar_id(calendar_name: str = "") -> str:
    name = str(calendar_name or "").strip()

    if not name:
        return "primary"

    calendars = list_calendars()

    matches = [
        calendar
        for calendar in calendars
        if str(calendar.get("summary", "")).strip().casefold()
        == name.casefold()
    ]

    if len(matches) == 1:
        return str(matches[0]["id"])

    if len(matches) > 1:
        raise ValueError(
            f"'{name}' adı ilə birdən çox calendar tapıldı."
        )

    raise ValueError(
        f"Calendar tapılmadı: {name}"
    )


def list_events(
    calendar_id: str = "primary",
    max_results: int = 10,
    time_min: str | None = None,
    time_max: str | None = None,
    query: str | None = None,
):
    service = get_calendar_service()

    kwargs: dict[str, Any] = {
        "calendarId": calendar_id,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }

    if time_min:
        kwargs["timeMin"] = time_min
    else:
        kwargs["timeMin"] = datetime.now(
            timezone.utc
        ).isoformat()

    if time_max:
        kwargs["timeMax"] = time_max

    if query:
        kwargs["q"] = query

    result = (
        service.events()
        .list(**kwargs)
        .execute()
    )

    return result.get("items", [])


def create_event(
    title: str,
    start_iso: str,
    end_iso: str | None = None,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
    all_day: bool = False,
):
    service = get_calendar_service()

    if all_day:
        start_date = _parse_date(start_iso)

        if end_iso:
            end_date = _parse_date(end_iso)
        else:
            end_date = start_date + timedelta(days=1)

        if end_date <= start_date:
            end_date = start_date + timedelta(days=1)

        event: dict[str, Any] = {
            "summary": title,
            "start": {
                "date": start_date.isoformat(),
            },
            "end": {
                "date": end_date.isoformat(),
            },
        }

    else:
        if not end_iso:
            raise ValueError(
                "Vaxtlı event üçün end_iso tələb olunur."
            )

        event = {
            "summary": title,
            "start": {
                "dateTime": _normalize_datetime(start_iso),
            },
            "end": {
                "dateTime": _normalize_datetime(end_iso),
            },
        }

    if description:
        event["description"] = description

    if location:
        event["location"] = location

    return (
        service.events()
        .insert(
            calendarId=calendar_id,
            body=event,
        )
        .execute()
    )


def delete_event(
    event_id: str,
    calendar_id: str = "primary",
) -> bool:
    service = get_calendar_service()

    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()

    return True


def _normalize_datetime(value: str) -> str:
    text = str(value or "").strip()

    parsed = datetime.fromisoformat(
        text.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        parsed = parsed.replace(tzinfo=local_tz)

    return parsed.isoformat()


def _parse_date(value: str) -> date:
    text = str(value or "").strip()

    if "T" in text or " " in text:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).date()

    return date.fromisoformat(text)