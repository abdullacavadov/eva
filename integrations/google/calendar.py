from __future__ import annotations

from datetime import datetime, timezone

from googleapiclient.discovery import build

from integrations.google.auth import get_calendar_credentials


def get_calendar_service():
    credentials = get_calendar_credentials()

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )


def list_events(
    calendar_id: str = "primary",
    max_results: int = 10,
):
    service = get_calendar_service()

    now = datetime.now(timezone.utc).isoformat()

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return result.get("items", [])


def create_event(
    title: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
):
    service = get_calendar_service()

    event = {
        "summary": title,
        "start": {
            "dateTime": start_iso,
        },
        "end": {
            "dateTime": end_iso,
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
):
    service = get_calendar_service()

    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()

    return True