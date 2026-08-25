"""Quiet-hours sonrası proaktiv notification-ları qruplaşdırmaq üçün köməkçi."""

from __future__ import annotations

from collections import Counter
from typing import Any


def build_notification_digest(pending: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Pending event-ləri mənbə üzrə bir xülasə notification-a çevirir."""
    if not pending:
        return None

    counts = Counter(str(event.get("source", "unknown")) for event in pending.values())
    labels = {
        "whatsapp": "WhatsApp",
        "gmail": "Gmail",
        "calendar": "Təqvim",
        "tasks": "Tasks",
        "memory": "Memory",
    }
    parts = [
        f"{labels.get(source, source)}: {count}"
        for source, count in counts.items()
    ]
    total = sum(counts.values())

    return {
        "source": "digest",
        "count": total,
        "counts": dict(counts),
        "items": list(pending.values()),
        "title": "Proaktiv xülasə",
        "text": f"Quiet hours ərzində {total} yeni hadisə yığılıb — " + "; ".join(parts) + ".",
    }
