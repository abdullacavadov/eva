from __future__ import annotations

import re
from typing import Any

from core.result_context import ResultContext


class ResultResolutionError(ValueError):
    pass


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def _search_text(item: dict[str, Any]) -> str:
    fields = (
        "summary",
        "title",
        "display_name",
        "subject",
        "name",
        "snippet",
    )
    return " ".join(str(item.get(field, "")) for field in fields if item.get(field))


def resolve_item(context: ResultContext, query: str) -> dict[str, Any]:
    if not context.data:
        raise ResultResolutionError("Nəticə siyahısı boşdur")

    normalized_query = _normalize(query)
    if not normalized_query:
        raise ResultResolutionError("Seçim üçün axtarış mətni boşdur")

    exact = [
        item
        for item in context.data
        if normalized_query == _normalize(_search_text(item))
        or any(normalized_query == _normalize(item.get(field)) for field in ("summary", "title", "display_name", "subject", "name"))
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ResultResolutionError("Bir neçə uyğun nəticə tapıldı")

    matches = [
        item for item in context.data
        if normalized_query in _normalize(_search_text(item))
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ResultResolutionError("Bir neçə uyğun nəticə tapıldı")
    raise ResultResolutionError("Uyğun nəticə tapılmadı")
