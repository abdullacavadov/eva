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

    def save(self, result: dict) -> str:
        self._cleanup()
        result_id = f"r_{uuid4().hex}"
        context = ResultContext.from_result(result_id, result, self.ttl_seconds)
        self._results[result_id] = context
        self._order.append(result_id)
        while len(self._order) > self.max_results:
            self._results.pop(self._order.pop(0), None)
        return result_id

    def get(self, result_id: str) -> ResultContext | None:
        self._cleanup()
        return self._results.get(result_id)

    def current(self) -> ResultContext | None:
        self._cleanup()
        if not self._order:
            return None
        return self._results.get(self._order[-1])

    def clear(self) -> None:
        self._results.clear()
        self._order.clear()

    def _cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        self._order = [
            result_id
            for result_id in self._order
            if result_id in self._results and not self._results[result_id].is_expired(now)
        ]
        self._results = {result_id: self._results[result_id] for result_id in self._order}
