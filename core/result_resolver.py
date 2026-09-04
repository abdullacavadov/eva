from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.result_context import ResultContext


class ResultResolutionError(ValueError):
    pass


@dataclass(frozen=True)
class FollowUpAction:
    """Söhbət kontekstündən həll edilmiş follow-up əməlini təsvir edir."""

    reference: str
    action: str
    item: dict[str, Any]
    action_text: str = ""


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def _search_text(item: dict[str, Any]) -> str:
    fields = ("summary", "title", "display_name", "subject", "name", "snippet")
    return " ".join(str(item.get(field, "")) for field in fields if item.get(field))


def _selection_queries(query: str) -> list[str]:
    normalized = _normalize(query)
    queries = [normalized]
    stripped = re.sub(r"(?:[-\s]?(?:i|ı|u|ü|ni|nı|nu|nü))?\s+(?:aç|ac|göstər|goster|oxu|bax)$", "", normalized).strip()
    if stripped and stripped != normalized:
        queries.append(stripped)
    without_demonstrative = re.sub(r"^(?:həmin|həminin|bu|bunun|o)\s+", "", stripped).strip()
    if without_demonstrative and without_demonstrative != stripped:
        queries.append(without_demonstrative)
    stemmed = re.sub(r"(?:ni|nı|nu|nü|i|ı|u|ü)$", "", without_demonstrative).strip()
    if stemmed and stemmed != without_demonstrative:
        queries.append(stemmed)
    return list(dict.fromkeys(queries))


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
    ordinal_words = {
        "birinci", "birincini", "birincisi", "ikinci", "ikincini", "ikincisi",
        "üçüncü", "üçüncünü", "üçüncüsü", "dördüncü", "dördüncünü", "dördüncüsü",
        "beşinci", "beşincini", "beşincisi", "sonuncu", "sonuncunu", "sonuncusu",
    }
    if normalized.isdigit() or normalized in ordinal_words:
        return True
    return bool(re.fullmatch(r"(?:ona|onu|onun|o|bunu|buna|bunun|bu|həmin|həminini)(?:\s+(?:email|e-mail|mesaj|qeyd|tədbir|task))?", normalized))


def _extract_follow_up_reference(query: str) -> tuple[str, str]:
    original = re.sub(r"\s+", " ", str(query or "")).strip()
    if not original:
        raise ResultResolutionError("Follow-up sorğusu boşdur")
    normalized = _normalize(original)
    implicit_show = {
        "göstər", "goster", "göstər baxım", "goster baxim",
        "aç", "ac", "oxu", "bax",
        "modalda göstər", "modalda goster", "modalda aç", "modalda ac",
        "ekranda göstər", "ekranda goster", "ekranda aç", "ekranda ac",
        "bunu modalda göstər", "bunu modalda goster", "bunu ekranda göstər", "bunu ekranda goster",
        "həminini modalda göstər", "həminini modalda goster", "həminini ekranda göstər", "həminini ekranda goster",
    }
    if normalized in implicit_show:
        return "current", "göstər"

    # Modal/ekran sözləri ayrıca obyekt adı deyil; onlar göstərmə üsulunu bildirir.
    display_mode_match = re.match(
        r"^(?:(?:bunu|bunu|həminini|həmin|onu|onu)\s+)?(?:modalda|ekranda)\s+(göstər|goster|aç|ac)(?:\s+baxım|\s+baxim)?$",
        normalized,
        re.IGNORECASE,
    )
    if display_mode_match:
        return "current", "göstər"

    action_match = re.match(r"^(.+?)\s+(göstər|goster|aç|ac|oxu|bax)(?:\s+baxım|\s+baxim)?$", normalized, re.IGNORECASE)
    if action_match:
        reference_text = action_match.group(1).strip()
        if reference_text:
            return reference_text, "göstər"

    reference_pattern = (
        r"(?:birinci(?:ni|si)?|ikinci(?:ni|si)?|üçüncü(?:nü|sü)?|dördüncü(?:nü|sü)?|"
        r"beşinci(?:ni|si)?|sonuncu(?:nu|su)?|\d+|ona|onu|onun|o|bunu|buna|bunun|bu|həmin|həminini)"
        r"(?:\s+(?:email|e-mail|mesaj|qeyd|tədbir|task))?"
    )
    match = re.match(rf"^({reference_pattern})(?:\s+(.*))?$", original, re.IGNORECASE)
    if not match:
        raise ResultResolutionError("Follow-up sorğusunda nisbi istinad tapılmadı")
    return _normalize(match.group(1)), (match.group(2) or "").strip()


def _detect_follow_up_action(action_text: str) -> str:
    normalized = _normalize(action_text)
    if not normalized:
        return "show"
    if re.search(r"\b(göstər|goster|aç|ac|oxu|bax)\b", normalized):
        return "show"
    if re.search(r"\b(tamamla|bitir|yerinə yetir|yerine yetir)\b", normalized):
        return "complete"
    if re.search(r"\b(cavab yaz|cavab ver|cavabla|cavablandır|cavablandir)\b", normalized):
        return "reply"
    if re.search(r"\b(sil|poz|ləğv et|legv et)\b", normalized):
        return "delete"
    if re.search(r"\b(dəyiş|deyis|yenilə|yenile|keçir|kecir|köçür|koçur|təxirə sal|texire sal)\b", normalized):
        return "update"
    raise ResultResolutionError("Follow-up üçün tanınmayan əməl")


def resolve_follow_up_action(context: ResultContext, query: str, selected_item: dict[str, Any] | None = None) -> FollowUpAction:
    reference, action_text = _extract_follow_up_reference(query)
    if reference == "current":
        if not context.data:
            raise ResultResolutionError("Nəticə siyahısı boşdur")
        item = selected_item or context.data[0]
    elif _is_relative_reference(reference):
        item = resolve_reference(context, reference, selected_item=selected_item)
    else:
        item = resolve_item(context, reference)
    action = _detect_follow_up_action(action_text)
    return FollowUpAction(reference=reference, action=action, item=item, action_text=action_text)


def resolve_reference(context: ResultContext, query: str, selected_item: dict[str, Any] | None = None) -> dict[str, Any]:
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
        exact = [item for item in context.data if normalized_query == _normalize(_search_text(item)) or any(normalized_query == _normalize(item.get(field)) for field in ("summary", "title", "display_name", "subject", "name"))]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ResultResolutionError("Bir neçə uyğun nəticə tapıldı")
        matches = [item for item in context.data if normalized_query in _normalize(_search_text(item))]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ResultResolutionError("Bir neçə uyğun nəticə tapıldı")
    raise ResultResolutionError("Uyğun nəticə tapılmadı")
