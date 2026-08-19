from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StructuredResult:
    type: str
    status: str
    query: dict[str, Any] = field(default_factory=dict)
    data: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    selected: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.count = len(self.data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "status": self.status,
            "query": self.query,
            "data": self.data,
            "count": self.count,
            "selected": self.selected,
            "meta": self.meta,
        }


def success(result_type: str, data: list[dict[str, Any]], query: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return StructuredResult(result_type, "success", query or {}, data, meta=meta or {}).to_dict()


def empty(result_type: str, query: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return StructuredResult(result_type, "empty", query or {}, [], meta=meta or {}).to_dict()


def error(result_type: str, message: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
    return StructuredResult(result_type, "error", query or {}, [], meta={"message": message}).to_dict()
