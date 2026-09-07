"""EVA proaktiv bildirişləri üçün deterministik prioritet hesablaması."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


URGENT_TERMS = (
    "urgent",
    "vacib",
    "təcili",
    "tecilı",
    "deadline",
    "son tarix",
    "immediate",
    "asap",
)


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key, ""))
        for key in ("subject", "title", "summary", "name", "body", "notes", "type")
    ).casefold()


def priority_score(event: dict[str, Any], now: datetime | None = None) -> int:
    """Hadisə üçün 0-100 arası deterministik prioritet hesablayır.

    Bu mərhələdə LLM çağırışı edilmir və mövcud notification davranışı dəyişmir.
    Hesablamanın məqsədi pending hadisələri daha faydalı ardıcıllıqla seçməkdir.
    """
    now = now or datetime.now().astimezone()
    source = str(event.get("source", "")).casefold()
    item = event.get("item") or {}
    if not isinstance(item, dict):
        item = {}

    score = {
        "calendar": 70,
        "tasks": 65,
        "whatsapp": 55,
        "gmail": 45,
        "memory": 35,
    }.get(source, 20)

    text = _text(item)
    if any(term in text for term in URGENT_TERMS):
        score += 25

    if source == "whatsapp":
        unread = max(0, int(item.get("unread_count", 0) or 0))
        if unread >= 5:
            score += 15
        elif unread >= 2:
            score += 8

    if source == "tasks":
        due = _parse_datetime(item.get("due") or item.get("date"))
        if due is not None:
            delta = due - now
            if delta <= timedelta(hours=0):
                score += 25
            elif delta <= timedelta(hours=2):
                score += 20
            elif delta <= timedelta(hours=24):
                score += 10

    if source == "calendar":
        start = _parse_datetime(item.get("start") or item.get("date"))
        if start is not None:
            delta = start - now
            if timedelta(0) <= delta <= timedelta(minutes=15):
                score += 20
            elif timedelta(0) <= delta <= timedelta(hours=1):
                score += 10
            elif delta < timedelta(0) and delta >= -timedelta(minutes=15):
                score += 15

    if bool(event.get("changed")):
        score += 5

    return max(0, min(100, score))


def rank_events(events: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    """Hadisələri prioritetə görə sıralayır; giriş siyahısını mutasiya etmir."""
    now = now or datetime.now().astimezone()
    return sorted(
        events,
        key=lambda event: (-priority_score(event, now), str(event.get("key", ""))),
    )
