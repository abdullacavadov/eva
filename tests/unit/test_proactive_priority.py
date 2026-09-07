from __future__ import annotations

from datetime import datetime, timezone

from core.proactive_priority import priority_score, rank_events


NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def test_urgent_email_outranks_normal_email():
    normal = {
        "key": "gmail:normal",
        "source": "gmail",
        "item": {"subject": "Newsletter"},
    }
    urgent = {
        "key": "gmail:urgent",
        "source": "gmail",
        "item": {"subject": "Təcili: server deadline"},
    }

    ranked = rank_events([normal, urgent], NOW)

    assert [event["key"] for event in ranked] == ["gmail:urgent", "gmail:normal"]


def test_near_calendar_event_gets_high_priority():
    event = {
        "source": "calendar",
        "item": {"title": "Meeting", "start": "2026-09-07T12:10:00+00:00"},
    }

    assert priority_score(event, NOW) > priority_score(
        {"source": "gmail", "item": {"subject": "Newsletter"}}, NOW
    )


def test_overdue_task_gets_higher_priority_than_future_task():
    overdue = {
        "source": "tasks",
        "item": {"title": "Fix issue", "due": "2026-09-07T11:00:00+00:00"},
    }
    future = {
        "source": "tasks",
        "item": {"title": "Plan work", "due": "2026-09-08T11:00:00+00:00"},
    }

    assert priority_score(overdue, NOW) > priority_score(future, NOW)


def test_whatsapp_unread_volume_affects_priority():
    low = {
        "source": "whatsapp",
        "item": {"title": "Ali", "unread_count": 1},
    }
    high = {
        "source": "whatsapp",
        "item": {"title": "Ali", "unread_count": 6},
    }

    assert priority_score(high, NOW) > priority_score(low, NOW)


def test_rank_events_does_not_mutate_input():
    events = [
        {"key": "gmail:1", "source": "gmail", "item": {"subject": "Normal"}},
        {"key": "gmail:2", "source": "gmail", "item": {"subject": "Urgent deadline"}},
    ]
    original_keys = [event["key"] for event in events]

    rank_events(events, NOW)

    assert [event["key"] for event in events] == original_keys
