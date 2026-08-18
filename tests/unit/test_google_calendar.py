from unittest.mock import MagicMock, patch

from integrations.google.calendar import (
    create_event,
    delete_event,
    list_events,
)


def mock_service():
    service = MagicMock()
    return service


@patch("integrations.google.calendar.get_calendar_service")
def test_list_events(mock_get_service):
    service = mock_service()
    service.events.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "1", "summary": "Test event"},
        ]
    }
    mock_get_service.return_value = service

    result = list_events()

    assert result == [{"id": "1", "summary": "Test event"}]

    service.events.return_value.list.assert_called_once_with(
        calendarId="primary",
        timeMin=service.events.return_value.list.call_args.kwargs["timeMin"],
        maxResults=10,
        singleEvents=True,
        orderBy="startTime",
    )


@patch("integrations.google.calendar.get_calendar_service")
def test_create_event(mock_get_service):
    service = mock_service()
    service.events.return_value.insert.return_value.execute.return_value = {
        "id": "event-123",
        "summary": "Test event",
    }
    mock_get_service.return_value = service

    result = create_event(
        title="Test event",
        start_iso="2026-08-20T10:00:00+04:00",
        end_iso="2026-08-20T11:00:00+04:00",
        description="Description",
        location="Baku",
    )

    assert result["id"] == "event-123"

    service.events.return_value.insert.assert_called_once_with(
        calendarId="primary",
        body={
            "summary": "Test event",
            "start": {
                "dateTime": "2026-08-20T10:00:00+04:00",
            },
            "end": {
                "dateTime": "2026-08-20T11:00:00+04:00",
            },
            "description": "Description",
            "location": "Baku",
        },
    )


@patch("integrations.google.calendar.get_calendar_service")
def test_delete_event(mock_get_service):
    service = mock_service()
    service.events.return_value.delete.return_value.execute.return_value = None
    mock_get_service.return_value = service

    result = delete_event("event-123")

    assert result is True

    service.events.return_value.delete.assert_called_once_with(
        calendarId="primary",
        eventId="event-123",
    )