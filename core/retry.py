"""Small retry helper for idempotent integration reads.

Yazma əməliyyatları üçün avtomatik retry istifadə edilməməlidir: timeout zamanı
əməliyyatın serverdə icra olunub-olunmadığı bilinməyə bilər.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    """Bütün təhlükəsiz retry cəhdləri uğursuz olduqda istifadə olunur."""

    def __init__(self, operation: str, attempts: int, last_error: Exception):
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"{operation} failed after {attempts} attempts: {last_error}")


def is_transient_error(exc: Exception) -> bool:
    """Yalnız şəbəkə/rate-limit xarakterli səhvləri retry üçün uyğun sayır."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "resp", None)
        status = getattr(status, "status", None)
    if status in {408, 429, 500, 502, 503, 504}:
        return True
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    return any(token in name or token in text for token in (
        "timeout", "timedout", "connectionreset", "connectionerror",
        "temporarily unavailable", "rate limit", "too many requests",
    ))


def retry_read(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """İdempotent read əməliyyatını yalnız transient error zamanı təkrar edir."""
    attempts = max(1, int(attempts))
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt >= attempts or not is_transient_error(exc):
                raise
            sleep(max(0.0, float(base_delay)) * (2 ** (attempt - 1)))
    assert last_error is not None
    raise RetryExhaustedError(getattr(operation, "__name__", "read"), attempts, last_error)
