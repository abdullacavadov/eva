from __future__ import annotations

from core.proactive_correlation import correlate_events
from core.proactive_priority import priority_score


def _event(key: str, source: str, title: str, **item):
    return {
        "key": key,
        "source": source,
        "item": {"title": title, **item},
        "changed": True,
    }


def test_correlates_calendar_and_gmail_by_shared_topic():
    events = [
        _event("gmail:1", "gmail", "Project Apollo meeting tomorrow"),
        _event("calendar:1", "calendar", "Project Apollo meeting", start="2026-09-08T10:00:00+04:00"),
        _event("gmail:2", "gmail", "Weekly newsletter"),
    ]

    result = correlate_events(events)

    assert len(result) == 2
    correlated = next(event for event in result if event["source"] == "correlated")
    assert correlated["_correlated_keys"] == ["gmail:1", "calendar:1"]


def test_correlates_events_by_shared_participant_email():
    events = [
        _event("gmail:1", "gmail", "Budget review", **{"from": "ali@example.com"}),
        _event(
            "calendar:1",
            "calendar",
            "Budget review",
            attendees=[{"email": "ali@example.com"}],
            start="2026-09-08T10:00:00+04:00",
        ),
    ]

    result = correlate_events(events)

    assert len(result) == 1
    assert result[0]["source"] == "correlated"


def test_does_not_correlate_same_source_or_unrelated_topics():
    events = [
        _event("gmail:1", "gmail", "Payment invoice"),
        _event("gmail:2", "gmail", "Payment invoice reminder"),
        _event("calendar:1", "calendar", "Dentist appointment"),
    ]

    result = correlate_events(events)

    assert len(result) == 3
    assert all(event["source"] != "correlated" for event in result)


def test_correlated_priority_uses_highest_child_priority_plus_bonus():
    events = [
        _event("gmail:1", "gmail", "URGENT payment deadline"),
        _event("tasks:1", "tasks", "Pay invoice", due="2026-09-07T15:00:00+04:00"),
    ]

    correlated = correlate_events(events)[0]

    assert correlated["source"] == "correlated"
    assert priority_score(correlated) > priority_score(events[0])
