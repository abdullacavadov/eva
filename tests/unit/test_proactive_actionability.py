from __future__ import annotations

from core.proactive_actionability import classify_actionability, is_noise, prepare_proactive_events


def _event(source: str, title: str, **item):
    return {"key": f"{source}:1", "source": source, "item": {"title": title, **item}, "changed": True}


def test_gmail_newsletter_is_suppressed():
    event = _event("gmail", "Weekly newsletter")
    assert is_noise(event) is True
    assert prepare_proactive_events([event]) == []


def test_gmail_with_promotion_label_is_suppressed():
    event = _event("gmail", "Special offer", labels=["PROMOTIONS"])
    assert is_noise(event) is True


def test_normal_gmail_is_not_suppressed():
    event = _event("gmail", "Client payment approval")
    assert is_noise(event) is False


def test_actionability_classifies_urgent_first():
    event = _event("gmail", "URGENT payment deadline")
    assert classify_actionability(event) == "urgent"


def test_tasks_and_calendar_are_actionable():
    assert classify_actionability(_event("tasks", "Buy supplies")) == "actionable"
    assert classify_actionability(_event("calendar", "Meeting")) == "actionable"


def test_plain_gmail_is_informational():
    event = _event("gmail", "Project update")
    assert classify_actionability(event) == "informational"


def test_rank_events_adds_actionability_without_mutating_input():
    event = _event("gmail", "Project update")
    prepared = prepare_proactive_events([event])
    assert prepared[0]["actionability"] == "informational"
    assert "actionability" not in event
