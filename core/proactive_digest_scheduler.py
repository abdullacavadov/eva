"""Quiet-hours digest üçün ProactiveScheduler adapteri."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from core.notification_digest import build_notification_digest


class ProactiveDigestScheduler:
    """Mövcud ProactiveEngine ilə digest delivery-ni təhlükəsiz şəkildə idarə edir.

    Bu adapter mövcud scheduler contract-ını dəyişmir. Digest yalnız caller
    tərəfindən quiet-hours transition təsdiqləndikdə yaradılır və delivery
    uğursuz olarsa child event-lər ACK edilmir.
    """

    def __init__(self, engine: Any, on_notification: Callable[[dict[str, Any]], Any]) -> None:
        self.engine = engine
        self.on_notification = on_notification

    def build(self) -> dict[str, Any] | None:
        state = self.engine._load()
        return build_notification_digest(state.get("pending", {}))

    def deliver(self, digest: dict[str, Any]) -> bool:
        result = self.on_notification(digest)
        return result is not False

    def acknowledge(self, digest: dict[str, Any], sent_at: datetime | None = None) -> bool:
        if not self.deliver(digest):
            return False

        state = self.engine._load()
        pending = state.get("pending", {})
        history = state.get("history", {})
        timestamp = (sent_at or datetime.now().astimezone()).isoformat()

        for event in digest.get("items", []):
            key = str(event.get("key", ""))
            if key and key in pending:
                history[key] = timestamp
                pending.pop(key, None)

        state["pending"] = pending
        state["history"] = history
        self.engine._save(state)
        return True
