from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class ResultContext:
    result_id: str
    type: str
    query: dict[str, Any]
    data: list[dict[str, Any]]
    count: int
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_result(cls, result_id: str, result: dict[str, Any], ttl_seconds: int) -> "ResultContext":
        now = datetime.now(timezone.utc)
        data = result.get("data") or []
        return cls(
            result_id=result_id,
            type=result.get("type", ""),
            query=result.get("query") or {},
            data=data,
            count=result.get("count", len(data)),
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(timezone.utc)) >= self.expires_at
