from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.result_context import ResultContext


@dataclass(frozen=True)
class ConversationState:
    """Aktiv söhbətin strukturlaşdırılmış kontekstünü saxlayır."""

    result_id: str | None = None
    intent: str = ""
    entity: str = ""
    selected_id: str | None = None
    action: str = ""
    updated_at: datetime | None = None

    def is_expired(self, ttl_seconds: int, now: datetime | None = None) -> bool:
        if self.updated_at is None:
            return True
        current = now or datetime.now(timezone.utc)
        return current - self.updated_at >= timedelta(seconds=ttl_seconds)


class ResultStore:
    def __init__(self, ttl_seconds: int = 1800, max_results: int = 10) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_results <= 0:
            raise ValueError("max_results must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_results = max_results
        self._results: dict[str, ResultContext] = {}
        self._order: list[str] = []
        self._selected: dict[str, str] = {}
        self._conversation = ConversationState()

    def save(self, result: dict) -> str:
        self._cleanup()
        result_id = f"r_{uuid4().hex}"
        context = ResultContext.from_result(result_id, result, self.ttl_seconds)
        self._results[result_id] = context
        self._order.append(result_id)
        query = result.get("query") or {}
        meta = result.get("meta") or {}
        self._conversation = ConversationState(
            result_id=result_id,
            intent=str(query.get("intent", "") or ""),
            entity=str(meta.get("entity", "") or ""),
            selected_id=str(meta.get("selected_id")) if meta.get("selected_id") else None,
            action=str(meta.get("action", "") or ""),
            updated_at=datetime.now(timezone.utc),
        )
        while len(self._order) > self.max_results:
            removed_id = self._order.pop(0)
            self._results.pop(removed_id, None)
            self._selected.pop(removed_id, None)
        return result_id

    def get(self, result_id: str) -> ResultContext | None:
        self._cleanup()
        return self._results.get(result_id)

    def current(self) -> ResultContext | None:
        self._cleanup()
        if not self._order:
            return None
        return self._results.get(self._order[-1])

    def conversation(self, now: datetime | None = None) -> ConversationState | None:
        self._cleanup()
        if self._conversation.is_expired(self.ttl_seconds, now):
            self._conversation = ConversationState()
            return None
        if self._conversation.result_id and self._conversation.result_id not in self._results:
            self._conversation = ConversationState()
            return None
        return self._conversation

    def update_conversation(self, *, action: str | None = None, selected_id: str | None = None) -> ConversationState:
        current = self.conversation() or ConversationState()
        self._conversation = ConversationState(
            result_id=current.result_id,
            intent=current.intent,
            entity=current.entity,
            selected_id=selected_id if selected_id is not None else current.selected_id,
            action=action if action is not None else current.action,
            updated_at=datetime.now(timezone.utc),
        )
        return self._conversation

    def clear_conversation(self) -> None:
        self._conversation = ConversationState()

    def select(self, result_id: str, item_id: str) -> dict:
        context = self.get(result_id)
        if context is None:
            raise KeyError(result_id)
        item = next((item for item in context.data if item.get("id") == item_id), None)
        if item is None:
            raise KeyError(item_id)
        self._selected[result_id] = item_id
        current = self.conversation()
        if current and current.result_id == result_id:
            self.update_conversation(selected_id=item_id)
        return item

    def selected(self, result_id: str | None = None) -> dict | None:
        context = self.get(result_id) if result_id else self.current()
        if context is None:
            return None
        item_id = self._selected.get(context.result_id)
        if item_id is None:
            return None
        return next((item for item in context.data if item.get("id") == item_id), None)

    def clear(self) -> None:
        self._results.clear()
        self._order.clear()
        self._selected.clear()
        self.clear_conversation()

    def _cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        self._order = [
            result_id
            for result_id in self._order
            if result_id in self._results and not self._results[result_id].is_expired(now)
        ]
        self._results = {result_id: self._results[result_id] for result_id in self._order}
        self._selected = {
            result_id: item_id
            for result_id, item_id in self._selected.items()
            if result_id in self._results
        }
