"""EVA proaktiv hadisələri üçün deterministik cross-source korrelyasiya."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

_STOP_WORDS = {
    "the", "and", "for", "with", "from", "this", "that", "new", "email",
    "meeting", "task", "calendar", "message", "whatsapp", "gmail",
    "bir", "bu", "və", "ile", "üçün", "olan", "olanı", "yeni", "tapşırıq",
    "təqvim", "mesaj", "görüş",
}
_DATE_KEYS = ("start", "due", "date", "datetime", "timestamp", "internalDate")
_TEXT_KEYS = ("subject", "title", "summary", "name", "body", "notes")
_PARTICIPANT_KEYS = ("from", "email", "to", "attendees", "participants", "organizer")


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _tokens(item: dict[str, Any]) -> set[str]:
    text = " ".join(str(item.get(key, "")) for key in _TEXT_KEYS).casefold()
    return {
        token
        for token in re.findall(r"[a-z0-9əğıöşüç]{3,}", text)
        if token not in _STOP_WORDS
    }


def _participants(item: dict[str, Any]) -> set[str]:
    values: list[str] = []
    for key in _PARTICIPANT_KEYS:
        value = item.get(key)
        if isinstance(value, list):
            values.extend(str(entry) for entry in value)
        elif isinstance(value, dict):
            values.extend(str(entry) for entry in value.values())
        elif value:
            values.append(str(value))
    return set(re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", " ".join(values).casefold()))


def _event_datetime(event: dict[str, Any]) -> datetime | None:
    item = event.get("item") or {}
    if not isinstance(item, dict):
        return None
    for key in _DATE_KEYS:
        parsed = _parse_datetime(item.get(key))
        if parsed is not None:
            return parsed
    return None


def _related(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("source") == right.get("source"):
        return False

    left_item = left.get("item") or {}
    right_item = right.get("item") or {}
    if not isinstance(left_item, dict) or not isinstance(right_item, dict):
        return False

    left_date = _event_datetime(left)
    right_date = _event_datetime(right)
    if left_date and right_date and abs(left_date - right_date) > timedelta(hours=48):
        return False

    shared_participants = _participants(left_item) & _participants(right_item)
    if shared_participants:
        return True

    shared_tokens = _tokens(left_item) & _tokens(right_item)
    return len(shared_tokens) >= 2


def correlate_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Əlaqəli müxtəlif mənbə hadisələrini bir notification-da qruplaşdırır.

    Yalnız artıq policy tərəfindən eligible hesab edilən hadisələr verilməlidir.
    Giriş siyahısı mutasiya edilmir; əlaqəsiz hadisələr olduğu kimi qaytarılır.
    """
    if len(events) < 2:
        return list(events)

    groups: list[list[dict[str, Any]]] = []
    assigned: set[int] = set()

    for index, event in enumerate(events):
        if index in assigned:
            continue
        group = [event]
        assigned.add(index)
        for other_index in range(index + 1, len(events)):
            if other_index in assigned:
                continue
            if any(_related(member, events[other_index]) for member in group):
                group.append(events[other_index])
                assigned.add(other_index)
        groups.append(group)

    result: list[dict[str, Any]] = []
    for group in groups:
        if len(group) == 1:
            result.append(group[0])
            continue
        primary = max(group, key=lambda event: {"calendar": 3, "tasks": 2, "whatsapp": 1, "gmail": 1, "memory": 0}.get(str(event.get("source")), 0))
        merged = dict(primary)
        merged["source"] = "correlated"
        merged["item"] = dict(primary.get("item") or {})
        merged["_correlated_events"] = [dict(event) for event in group]
        merged["_correlated_keys"] = [str(event.get("key")) for event in group if event.get("key")]
        merged["key"] = str(primary.get("key"))
        merged["changed"] = any(bool(event.get("changed")) for event in group)
        result.append(merged)

    return result
