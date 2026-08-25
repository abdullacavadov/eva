from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from actions.calendar import get_calendar_events
from actions.daily_report import build_daily_report
from actions.email import search_emails
from actions.whatsapp_read_action import read_whatsapp_messages
from actions.agenda import get_daily_agenda
from memory.memory_manager import load_memory
from core.query_planner import QueryPlan, plan_query
from core.unified_results import make_unified_result, normalize_item


def _date_query(period: str) -> str:
    today = datetime.now().astimezone().date()
    if period == "tomorrow":
        target = today + timedelta(days=1)
    else:
        target = today
    return target.isoformat()


def _memory_items(search_text: str = "", period: str = "") -> list[dict[str, Any]]:
    memory = load_memory()
    needle = str(search_text or "").casefold().strip()
    target_date = _date_query(period) if period else ""
    found: list[dict[str, Any]] = []

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            if "value" in value or "title" in value:
                text = " ".join(str(value.get(k, "")) for k in ("title", "value", "notes", "due", "type"))
                if (not needle or needle in text.casefold()) and (not target_date or target_date in text):
                    key = path or "memory"
                    found.append({
                        "id": f"memory:{key}",
                        "title": str(value.get("title") or value.get("value") or key),
                        "value": str(value.get("value", "")),
                        "notes": str(value.get("notes", "")),
                        "due": str(value.get("due", "")),
                        "type": str(value.get("type", "note")),
                        "source": "memory",
                    })
            for key, child in value.items():
                walk(child, f"{path}:{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}:{index}" if path else str(index))

    walk(memory)
    unique: dict[str, dict[str, Any]] = {item["id"]: item for item in found}
    return list(unique.values())[:20]


def _matches_search_terms(item: dict[str, Any], search_terms: tuple[str, ...]) -> bool:
    if not search_terms:
        return True
    text = " ".join(
        str(item.get(key, ""))
        for key in ("title", "value", "notes", "due", "description", "name")
    ).casefold()
    return any(term.casefold() in text for term in search_terms)


def _append_source(items: list[dict[str, Any]], source: str, result: Any, limit: int = 8, search_terms: tuple[str, ...] = ()) -> None:
    if not isinstance(result, dict):
        return
    matched = 0
    for raw in result.get("data", []):
        if not isinstance(raw, dict) or not _matches_search_terms(raw, search_terms):
            continue
        items.append(normalize_item(source, raw, result.get("type", "item")))
        matched += 1
        if matched >= limit:
            break


def _execute_daily_report(limit: int) -> dict[str, Any]:
    target_date = datetime.now().astimezone().date().isoformat()
    agenda = get_daily_agenda(limit=limit, date_text=target_date)
    results: dict[str, dict[str, Any]] = {
        "calendar": {"status": agenda.get("status"), "data": agenda.get("meta", {}).get("groups", {}).get("calendar", []), "meta": {"message": agenda.get("meta", {}).get("errors", {}).get("calendar", "")}},
        "tasks": {"status": agenda.get("status"), "data": agenda.get("meta", {}).get("groups", {}).get("tasks", []), "meta": {"message": agenda.get("meta", {}).get("errors", {}).get("tasks", "")}},
        "memory": {"status": agenda.get("status"), "data": agenda.get("meta", {}).get("groups", {}).get("memory", []), "meta": {"message": agenda.get("meta", {}).get("errors", {}).get("memory", "")}},
    }
    try:
        results["gmail"] = search_emails(
            f"after:{target_date.replace('-', '/')} before:{(datetime.fromisoformat(target_date) + timedelta(days=1)).strftime('%Y/%m/%d')}",
            limit,
        )
    except Exception as exc:
        results["gmail"] = {"status": "error", "data": [], "meta": {"message": str(exc)}}
    try:
        results["whatsapp"] = read_whatsapp_messages("", deduplicate=False)
    except Exception as exc:
        results["whatsapp"] = {"status": "error", "data": [], "meta": {"message": str(exc)}}
    return build_daily_report(results, target_date)


def execute_unified_query(query: str, limit: int = 8) -> dict[str, Any]:
    plan: QueryPlan = plan_query(query)
    if not plan.sources:
        return make_unified_result(query, plan.intent, [], [], meta={"reason": "No unified source matched; use the existing specialist tools."})
    limit = max(1, min(int(limit or 8), 20))
    if plan.intent == "daily_report":
        return _execute_daily_report(limit)

    items: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for source in plan.sources:
        try:
            if source == "calendar":
                result = get_calendar_events(plan.period or plan.search_text or "today", limit)
                _append_source(items, source, result, limit, plan.search_terms)
                if result.get("status") == "error":
                    errors[source] = result.get("meta", {}).get("message", "Calendar xətası")
            elif source == "tasks":
                from actions.reminders import get_reminders
                task_query = plan.period or plan.search_text or "upcoming"
                result = get_reminders(task_query, limit, "")
                _append_source(items, source, result, limit, plan.search_terms)
                if result.get("status") == "error":
                    errors[source] = result.get("meta", {}).get("message", "Google Tasks xətası")
            elif source == "memory":
                memory_search_text = " ".join(plan.search_terms) if plan.search_terms else plan.search_text
                for raw in _memory_items(memory_search_text, plan.period)[:limit]:
                    items.append(normalize_item(source, raw, "memory"))
            elif source == "gmail":
                q = plan.search_text
                if plan.period:
                    target = datetime.fromisoformat(_date_query(plan.period))
                    next_day = target + timedelta(days=1)
                    q = f"after:{target.strftime('%Y/%m/%d')} before:{next_day.strftime('%Y/%m/%d')}"
                result = search_emails(q, limit)
                _append_source(items, source, result, limit)
                if result.get("status") == "error":
                    errors[source] = result.get("meta", {}).get("message", "Gmail xətası")
            elif source == "whatsapp":
                result = read_whatsapp_messages(plan.search_text, deduplicate=True)
                _append_source(items, source, result, limit)
                if result.get("status") == "error":
                    errors[source] = result.get("meta", {}).get("message", "WhatsApp xətası")
        except Exception as exc:
            errors[source] = str(exc)
    unique: dict[str, dict[str, Any]] = {}
    for item in items:
        unique.setdefault(item["id"], item)
    ordered = list(unique.values())[: limit * max(1, len(plan.sources))]
    return make_unified_result(query, plan.intent, list(plan.sources), ordered, errors, {"period": plan.period, "search_text": plan.search_text, "search_terms": list(plan.search_terms), "requires_confirmation": plan.needs_confirmation, "source_count": len(plan.sources)})
