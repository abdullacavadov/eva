from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnifiedItem:
    id: str
    source: str
    type: str
    title: str
    timestamp: str = ""
    priority: str = "normal"
    status: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "title": self.title,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "status": self.status,
            "payload": self.payload,
        }


def normalize_item(source: str, item: dict[str, Any], default_type: str = "item") -> dict[str, Any]:
    item_id = str(item.get("id", "")) or f"{source}:unknown"
    title = str(
        item.get("title")
        or item.get("summary")
        or item.get("subject")
        or item.get("name")
        or item.get("conversation")
        or item_id
    )
    timestamp = str(
        item.get("timestamp")
        or item.get("start")
        or item.get("start_iso")
        or item.get("due")
        or item.get("date")
        or ""
    )
    priority = str(item.get("priority", "normal") or "normal")
    status = str(item.get("status", "") or "")
    return UnifiedItem(
        id=item_id,
        source=source,
        type=str(item.get("type", default_type) or default_type),
        title=title,
        timestamp=timestamp,
        priority=priority,
        status=status,
        payload=dict(item),
    ).to_dict()


def make_unified_result(
    query: str,
    intent: str,
    sources: list[str],
    items: list[dict[str, Any]],
    errors: dict[str, str] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "unified_query",
        "status": "success" if items else ("error" if errors and not sources else "empty"),
        "query": {"text": query, "intent": intent, "sources": sources},
        "data": items,
        "count": len(items),
        "selected": None,
        "meta": {"errors": errors or {}, **(meta or {})},
    }
