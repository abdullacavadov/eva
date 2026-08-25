from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    sources: tuple[str, ...]
    period: str = ""
    search_text: str = ""
    search_terms: tuple[str, ...] = ()
    needs_confirmation: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


_DAILY = ("calendar", "tasks", "memory")
_REPORT = ("gmail", "whatsapp", "calendar", "tasks", "memory")


def plan_query(query: str) -> QueryPlan:
    text = str(query or "").strip()
    q = text.casefold()
    if not text:
        return QueryPlan("unknown", tuple(), metadata={"reason": "empty_query"})

    deletion = any(word in q for word in ("sil", "silə", "silin", "delete", "poz"))
    if deletion:
        sources = []
        if any(word in q for word in ("task", "tapşır", "xatırlat")):
            sources.append("tasks")
        if any(word in q for word in ("təqvim", "calendar", "görüş", "tədbir")):
            sources.append("calendar")
        if any(word in q for word in ("yaddaş", "memory", "qeyd")):
            sources.append("memory")
        return QueryPlan("deletion", tuple(sources) or ("tasks", "calendar", "memory"), needs_confirmation=True, metadata={"ambiguous_source": "true" if not sources else "false"})

    if any(phrase in q for phrase in ("bu gün nə baş verib", "bu gün nə baş verdi", "bu gün üçün report", "bu gün üçün hesabat", "bugünkü report", "bugünkü hesabat", "gündəlik report", "daily report", "günlük report", "günlük hesabat")):
        return QueryPlan("daily_report", _REPORT, "today")

    if any(phrase in q for phrase in ("bu gün nə işim var", "bu gün nə etməliyəm", "bu gün nələr var", "bu gün planım", "bugün nə işim var")):
        return QueryPlan("agenda_query", _DAILY, "today")

    if any(phrase in q for phrase in ("sabah nə etməliyəm", "sabah nə işim var", "sabah nələr var", "sabah planım")):
        return QueryPlan("agenda_query", _DAILY, "tomorrow")

    if "əhməd" in q or "ahmed" in q:
        if any(word in q for word in ("danış", "yazış", "mesaj", "son nə", "nə demiş")):
            return QueryPlan("contact_history", ("whatsapp", "memory"), "", text, ("Əhməd",))

    if any(word in q for word in ("market", "mağaza", "almalı", "getməyi nə vaxt", "planlaşdırmışdım")):
        terms = []
        if "market" in q:
            terms.append("market")
        if "mağaza" in q:
            terms.append("mağaza")
        if "almalı" in q:
            terms.append("almalı")
        return QueryPlan("cross_source_search", ("calendar", "tasks", "memory"), "", text, tuple(terms))

    if any(word in q for word in ("email", "gmail", "poçt", "məktub")):
        return QueryPlan("gmail_query", ("gmail",), "", text)
    if "whatsapp" in q or "mesaj" in q or "yazış" in q:
        return QueryPlan("whatsapp_query", ("whatsapp",), "", text)
    if any(word in q for word in ("kontakt", "əlaqə", "telefon nömrə")):
        return QueryPlan("contacts_query", ("contacts",), "", text)
    if any(word in q for word in ("təqvim", "calendar", "görüş", "tədbir")):
        return QueryPlan("calendar_query", ("calendar",), "", text)
    if any(word in q for word in ("task", "tapşır", "xatırlat", "to-do", "todo")):
        return QueryPlan("tasks_query", ("tasks",), "", text)
    if any(word in q for word in ("yaddaş", "memory", "qeyd")):
        return QueryPlan("memory_query", ("memory",), "", text)

    return QueryPlan("information", tuple(), "", text)
