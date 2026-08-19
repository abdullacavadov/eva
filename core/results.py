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


def make_result(
    result_type: str,
    status: str,
    query: dict[str, Any] | None = None,
    data: list[dict[str, Any]] | None = None,
    count: int | None = None,
    selected: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = StructuredResult(
        result_type,
        status,
        query or {},
        data or [],
        selected=selected,
        meta=meta or {},
    ).to_dict()
    if count is not None:
        result["count"] = count
    return result


def success(result_type: str, data: list[dict[str, Any]], query: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return make_result(result_type, "success", query=query, data=data, meta=meta)


def empty(result_type: str, query: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return make_result(result_type, "empty", query=query, data=[], meta=meta)


def error(result_type: str, message: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
    return make_result(result_type, "error", query=query, data=[], meta={"message": message})
