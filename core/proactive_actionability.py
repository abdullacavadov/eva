"""EVA proaktiv hadisələri üçün səs-küy filtri və fəaliyyət dərəcəsi."""

from __future__ import annotations

from typing import Any


_LOW_SIGNAL_TERMS = (
    "newsletter",
    "unsubscribe",
    "weekly digest",
    "daily digest",
    "promotional",
    "promotion",
    "marketing",
)
_URGENT_TERMS = (
    "urgent",
    "vacib",
    "təcili",
    "tecilı",
    "acil",
    "deadline",
    "son tarix",
    "asap",
    "immediate",
)
_ACTION_TERMS = (
    "please reply",
    "reply required",
    "action required",
    "approve",
    "approval",
    "confirm",
    "payment",
    "ödəniş",
    "ödeniş",
    "pay",
    "deadline",
    "son tarix",
    "due",
    "təcili",
    "urgent",
)


def _text(event: dict[str, Any]) -> str:
    item = event.get("item") or {}
    if not isinstance(item, dict):
        return ""
    return " ".join(
        str(item.get(key, ""))
        for key in ("subject", "title", "summary", "name", "body", "notes", "type")
    ).casefold()


def _labels(event: dict[str, Any]) -> set[str]:
    item = event.get("item") or {}
    if not isinstance(item, dict):
        return set()
    raw = item.get("labels") or item.get("categories") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return set()
    return {str(value).strip().casefold() for value in raw if str(value).strip()}


def is_noise(event: dict[str, Any]) -> bool:
    """Yalnız açıq şəkildə aşağı siqnallı proaktiv hadisələri süzür."""
    if str(event.get("source", "")).casefold() != "gmail":
        return False
    labels = _labels(event)
    if labels & {"promotions", "promotion", "social", "spam", "newsletter"}:
        return True
    text = _text(event)
    return any(term in text for term in _LOW_SIGNAL_TERMS)


def classify_actionability(event: dict[str, Any]) -> str:
    """Hadisəni informational, actionable və ya urgent kimi təsnif edir."""
    text = _text(event)
    source = str(event.get("source", "")).casefold()
    if any(term in text for term in _URGENT_TERMS):
        return "urgent"
    if source == "tasks":
        return "actionable"
    if source == "calendar":
        return "actionable"
    if source == "whatsapp":
        try:
            if int((event.get("item") or {}).get("unread_count", 0) or 0) > 0:
                return "actionable"
        except (TypeError, ValueError):
            pass
    if any(term in text for term in _ACTION_TERMS):
        return "actionable"
    return "informational"


def prepare_proactive_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Noise filtrləyir və hadisəyə actionability metadata əlavə edir.

    Giriş siyahısı və hadisə obyektləri mutasiya edilmir.
    """
    result: list[dict[str, Any]] = []
    for event in events:
        if is_noise(event):
            continue
        prepared = dict(event)
        prepared["actionability"] = classify_actionability(event)
        result.append(prepared)
    return result
