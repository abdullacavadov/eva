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


def _selection_queries(query: str) -> list[str]:
    normalized = _normalize(query)
    queries = [normalized]
    stripped = re.sub(r"(?:[-\s]?(?:i|ı|u|ü|ni|nı|nu|nü))?\s+(?:aç|ac|göstər|goster|oxu|bax)$", "", normalized).strip()
    if stripped and stripped != normalized:
        queries.append(stripped)
    return queries


def _ordinal_index(query: str, count: int) -> int | None:
    normalized = _normalize(query)
    words = {
        "birinci": 0, "birincini": 0, "birincisi": 0,
        "ikinci": 1, "ikincini": 1, "ikincisi": 1,
        "üçüncü": 2, "üçüncünü": 2, "üçüncüsü": 2,
        "dördüncü": 3, "dördüncünü": 3, "dördüncüsü": 3,
        "beşinci": 4, "beşincini": 4, "beşincisi": 4,
        "sonuncu": -1, "sonuncunu": -1, "sonuncusu": -1,
    }
    if normalized.isdigit():
        index = int(normalized) - 1
    else:
        index = words.get(normalized)
    if index is None:
        return None
    if index == -1:
        index = count - 1
    return index if 0 <= index < count else None


def _is_relative_reference(query: str) -> bool:
    normalized = _normalize(query)
    if not normalized:
        return False
    if _ordinal_index(normalized, 1) is not None:
        return True
    return bool(re.fullmatch(
        r"(?:ona|onu|onun|o|bunu|buna|bunun|bu|həmin|həminini)"
        r"(?:\s+(?:email|e-mail|mesaj|qeyd|tədbir|task))?",
        normalized,
    ))


def resolve_reference(
    context: ResultContext,
    query: str,
    selected_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Əvvəlki nəticədən nisbi istinadı konkret elementə çevirir."""
    if not context.data:
        raise ResultResolutionError("Nəticə siyahısı boşdur")

    normalized = _normalize(query)
    if not _is_relative_reference(normalized):
        return resolve_item(context, query)

    index = _ordinal_index(normalized, len(context.data))
    if index is not None:
        return context.data[index]

    if selected_item is not None:
        selected_id = selected_item.get("id")
        if selected_id:
            for item in context.data:
                if item.get("id") == selected_id:
                    return item

    if len(context.data) == 1:
        return context.data[0]

    raise ResultResolutionError("Nisbi istinad üçün konkret nəticə seçilməyib")


def resolve_item(context: ResultContext, query: str) -> dict[str, Any]:
    if not context.data:
        raise ResultResolutionError("Nəticə siyahısı boşdur")

    normalized_queries = _selection_queries(query)
    if not normalized_queries[0]:
        raise ResultResolutionError("Seçim üçün axtarış mətni boşdur")

    for normalized_query in normalized_queries:
        exact = [
            item
            for item in context.data
            if normalized_query == _normalize(_search_text(item))
            or any(
                normalized_query == _normalize(item.get(field))
                for field in ("summary", "title", "display_name", "subject", "name")
            )
        ]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ResultResolutionError("Bir neçə uyğun nəticə tapıldı")

        matches = [
            item
            for item in context.data
            if normalized_query in _normalize(_search_text(item))
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ResultResolutionError("Bir neçə uyğun nəticə tapıldı")

    raise ResultResolutionError("Uyğun nəticə tapılmadı")
