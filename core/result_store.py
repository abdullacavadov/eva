from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from core.result_context import ResultContext


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

    def save(self, result: dict) -> str:
        self._cleanup()
        result_id = f"r_{uuid4().hex}"
        context = ResultContext.from_result(result_id, result, self.ttl_seconds)
        self._results[result_id] = context
        self._order.append(result_id)
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

    def select(self, result_id: str, item_id: str) -> dict:
        context = self.get(result_id)
        if context is None:
            raise KeyError(result_id)
        item = next((item for item in context.data if item.get("id") == item_id), None)
        if item is None:
            raise KeyError(item_id)
        self._selected[result_id] = item_id
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
