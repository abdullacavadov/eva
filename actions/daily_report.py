"""Unified daily report synthesis across Gmail, WhatsApp, Calendar, Tasks and Memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.results import empty, success
from core.unified_results import normalize_item


def _priority(item: dict[str, Any]) -> int:
    text = " ".join(str(item.get(key, "")) for key in ("title", "subject", "snippet", "notes")).casefold()
    if any(word in text for word in ("urgent", "vacib", "təcili", "important", "deadline")):
        return 3
    if item.get("due") or item.get("date"):
        return 2
    return 1


def _label(source: str) -> str:
    return {"calendar": "Təqvim", "tasks": "Tapşırıqlar", "memory": "Yaddaş", "gmail": "Gmail", "whatsapp": "WhatsApp"}.get(source, source)


def build_daily_report(results: dict[str, dict[str, Any]], date_text: str = "") -> dict[str, Any]:
    target_date = str(date_text or datetime.now().astimezone().date().isoformat())
    grouped: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str] = {}
    for source, result in results.items():
        if not isinstance(result, dict):
            continue
        if result.get("status") == "error":
            errors[source] = str(result.get("meta", {}).get("message", "Mənbə xətası"))
        items = []
        for raw in result.get("data", []):
            if isinstance(raw, dict):
                item = normalize_item(source, raw, result.get("type", "item"))
                item["priority"] = _priority(item)
                items.append(item)
        if items:
            grouped[source] = items
    ranked = sorted((item for items in grouped.values() for item in items), key=lambda item: (-int(item.get("priority", 1)), str(item.get("date", item.get("due", ""))), str(item.get("title", ""))))
    highlights = []
    for item in ranked[:10]:
        title = str(item.get("title") or item.get("subject") or item.get("snippet") or "").strip()
        if title:
            highlights.append({"source": item.get("source", ""), "label": _label(str(item.get("source", ""))), "title": title, "priority": item.get("priority", 1), "date": item.get("date", ""), "due": item.get("due", "")})
    summary = {"date": target_date, "sections": [{"source": source, "label": _label(source), "count": len(items)} for source, items in grouped.items()], "highlights": highlights, "total_items": len(ranked), "errors": errors}
    if not ranked and errors:
        return empty("daily_report", {"date": target_date}, meta=summary)
    return success("daily_report", highlights, {"date": target_date}, meta=summary)
