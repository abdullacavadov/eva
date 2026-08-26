from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from actions.calendar import get_calendar_events, delete_calendar_event
from actions.daily_report import build_daily_report
from actions.email import search_emails
from actions.whatsapp_read_action import read_whatsapp_messages
from actions.agenda import get_daily_agenda
from actions.reminder_memory import get_reminders as get_memory_reminders, delete_reminder as delete_memory_reminder
from memory.memory_manager import load_memory, delete_memory
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
                    found.append({"id": f"memory:{key}", "title": str(value.get("title") or value.get("value") or key), "value": str(value.get("value", "")), "notes": str(value.get("notes", "")), "due": str(value.get("due", "")), "type": str(value.get("type", "note")), "source": "memory"})
            for key, child in value.items(): walk(child, f"{path}:{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value): walk(child, f"{path}:{index}" if path else str(index))
    walk(memory)
    unique: dict[str, dict[str, Any]] = {item["id"]: item for item in found}
    return list(unique.values())[:20]


def _entity_matches(item: dict[str, Any], entity: str) -> bool:
    if not entity: return True
    haystack = " ".join(str(value) for value in item.values() if value is not None).casefold()
    normalized = str(entity).casefold().strip()
    if normalized in haystack: return True
    tokens = [token for token in normalized.split() if len(token) >= 4]
    return bool(tokens) and any(token in haystack for token in tokens)


def _matches_search_terms(item: dict[str, Any], search_terms: tuple[str, ...]) -> bool:
    if not search_terms: return True
    text = " ".join(str(item.get(key, "")) for key in ("title", "value", "notes", "due", "description", "name")).casefold()
    return any(term.casefold() in text for term in search_terms)


def _append_source(items: list[dict[str, Any]], source: str, result: Any, limit: int = 8, entity: str = "", search_terms: tuple[str, ...] = ()) -> None:
    if not isinstance(result, dict): return
    matched = 0
    for raw in result.get("data", []):
        if not isinstance(raw, dict): continue
        if entity and not _entity_matches(raw, entity): continue
        if search_terms and not _matches_search_terms(raw, search_terms): continue
        items.append(normalize_item(source, raw, result.get("type", "item")))
        matched += 1
        if matched >= limit: break


def _deletion_candidates(plan: QueryPlan, limit: int) -> tuple[list[dict[str, Any]], dict[str, str]]:
    candidates: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    entity = plan.metadata.get("entity", "")
    if "calendar" in plan.sources:
        try:
            result = get_calendar_events("upcoming", max(limit, 50))
            for item in result.get("data", []):
                if not entity or _entity_matches(item, entity) or _matches_search_terms(item, plan.search_terms): candidates.append(normalize_item("calendar", item, result.get("type", "calendar_event")))
            if result.get("status") == "error": errors["calendar"] = result.get("meta", {}).get("message", "Calendar xətası")
        except Exception as exc: errors["calendar"] = str(exc)
    if "tasks" in plan.sources:
        try:
            from actions.reminders import get_reminders
            result = get_reminders("upcoming", max(limit, 50), "")
            for item in result.get("data", []):
                if not entity or _entity_matches(item, entity) or _matches_search_terms(item, plan.search_terms): candidates.append(normalize_item("tasks", item, result.get("type", "task")))
            if result.get("status") == "error": errors["tasks"] = result.get("meta", {}).get("message", "Google Tasks xətası")
        except Exception as exc: errors["tasks"] = str(exc)
    if "reminder" in plan.sources:
        try:
            result = get_memory_reminders("upcoming", max(limit, 50), include_completed=False)
            for item in result.get("data", []):
                if not entity or _entity_matches(item, entity) or _matches_search_terms(item, plan.search_terms): candidates.append(normalize_item("reminder", item, result.get("type", "reminder")))
            if result.get("status") == "error": errors["reminder"] = result.get("meta", {}).get("message", "Xatırlatma yaddaşı xətası")
        except Exception as exc: errors["reminder"] = str(exc)
    if "memory" in plan.sources:
        memory_items: dict[str, dict[str, Any]] = {}
        terms = plan.search_terms or (plan.search_text,)
        for term in terms:
            for item in _memory_items(term, plan.period): memory_items.setdefault(item["id"], item)
        for item in memory_items.values():
            if not entity or _entity_matches(item, entity) or _matches_search_terms(item, plan.search_terms): candidates.append(normalize_item("memory", item, "memory"))
    unique: dict[str, dict[str, Any]] = {item["id"]: item for item in candidates}
    return list(unique.values())[:10], errors


def _deletion_result(query: str, plan: QueryPlan, candidates: list[dict[str, Any]], errors: dict[str, str], meta: dict[str, Any]) -> dict[str, Any]:
    meta.setdefault("deleted", False)
    return make_unified_result(query, "deletion", list(plan.sources), candidates, errors, meta)


def execute_unified_deletion(query: str, selected_id: str = "", confirmed: bool = False, limit: int = 8) -> dict[str, Any]:
    plan = plan_query(query)
    if plan.intent != "deletion":
        return _deletion_result(query, plan, [], {}, {"deletion_safe": True, "message": "Bu sorğu silmə əmri deyil."})
    candidates, errors = _deletion_candidates(plan, max(1, min(int(limit or 8), 20)))
    if not candidates:
        return _deletion_result(query, plan, [], errors, {"requires_confirmation": True, "deletion_safe": True, "message": "Silinəcək uyğun qeyd tapılmadı."})
    if not confirmed or not selected_id:
        return _deletion_result(query, plan, candidates, errors, {"requires_confirmation": True, "deletion_safe": True, "selected_id": None, "message": "Silmək üçün konkret qeydi seç və açıq təsdiq ver."})
    matches = [item for item in candidates if item.get("id") == str(selected_id)]
    if len(matches) != 1:
        return _deletion_result(query, plan, candidates, errors, {"requires_confirmation": True, "deletion_safe": True, "selected_id": None, "message": "Seçilmiş qeyd bu sorğunun namizədləri arasında deyil; heç nə silinmədi."})
    item = matches[0]; source = item.get("source", ""); payload = item.get("payload", {}) or {}
    try:
        if source == "tasks":
            from actions.reminders import delete_reminder
            task_id = str(payload.get("google_task_id", ""))
            if not task_id: return _deletion_result(query, plan, [item], errors, {"requires_confirmation": True, "deletion_safe": True, "message": "Task üçün təhlükəsiz silmə ID-si tapılmadı."})
            result = delete_reminder(task_id, str(payload.get("task_list_id", "")))
        elif source == "reminder":
            result = delete_memory_reminder(str(payload.get("id", item.get("id", ""))))
        elif source == "calendar":
            result = delete_calendar_event(str(payload.get("title", "")), str(payload.get("start", "")))
        elif source == "memory":
            parts = str(item.get("id", "")).split(":", 2)
            if len(parts) != 3: return _deletion_result(query, plan, [item], errors, {"requires_confirmation": True, "deletion_safe": True, "message": "Memory qeydi üçün təhlükəsiz silmə yolu tapılmadı."})
            result_text = delete_memory(category=parts[1], key=parts[2])
            result = {"status": "success" if "silindi" in result_text.casefold() else "error", "type": "memory", "data": [], "meta": {"message": result_text, "deleted_id": item["id"]}}
        else:
            return _deletion_result(query, plan, [item], errors, {"requires_confirmation": True, "deletion_safe": True, "message": f"{source} üçün unified silmə dəstəyi yoxdur."})
    except Exception as exc:
        result = {"status": "error", "type": "deletion", "data": [], "meta": {"message": str(exc)}}
    if result.get("status") != "success":
        errors[source] = result.get("meta", {}).get("message", "Silmə əməliyyatı uğursuz oldu.")
        return _deletion_result(query, plan, [item], errors, {"requires_confirmation": True, "deletion_safe": True, "selected_id": item["id"], "message": errors[source]})
    return _deletion_result(query, plan, [], {}, {"requires_confirmation": False, "deletion_safe": True, "selected_id": item["id"], "deleted": True, "message": "Seçilmiş qeyd silindi."})


def _execute_daily_report(limit: int) -> dict[str, Any]:
    target_date = datetime.now().astimezone().date().isoformat()
    agenda = get_daily_agenda(limit=limit, date_text=target_date)
    results = {
        "calendar": {"status": agenda.get("status"), "data": agenda.get("meta", {}).get("groups", {}).get("calendar", []), "meta": {"message": agenda.get("meta", {}).get("errors", {}).get("calendar", "")}},
        "tasks": {"status": agenda.get("status"), "data": agenda.get("meta", {}).get("groups", {}).get("tasks", []), "meta": {"message": agenda.get("meta", {}).get("errors", {}).get("tasks", "")}},
        "memory": {"status": agenda.get("status"), "data": agenda.get("meta", {}).get("groups", {}).get("memory", []), "meta": {"message": agenda.get("meta", {}).get("errors", {}).get("memory", "")}},
    }
    try: results["gmail"] = search_emails(f"after:{target_date.replace('-', '/')} before:{(datetime.fromisoformat(target_date) + timedelta(days=1)).strftime('%Y/%m/%d')}", limit)
    except Exception as exc: results["gmail"] = {"status": "error", "data": [], "meta": {"message": str(exc)}}
    try: results["whatsapp"] = read_whatsapp_messages("", deduplicate=False)
    except Exception as exc: results["whatsapp"] = {"status": "error", "data": [], "meta": {"message": str(exc)}}
    return build_daily_report(results, target_date)


def execute_unified_query(query: str, limit: int = 8) -> dict[str, Any]:
    plan: QueryPlan = plan_query(query)
    if not plan.sources: return make_unified_result(query, plan.intent, [], [], meta={"reason": "No unified source matched; use the existing specialist tools."})
    limit = max(1, min(int(limit or 8), 20))
    if plan.intent == "daily_report": return _execute_daily_report(limit)
    if plan.intent == "deletion":
        candidates, errors = _deletion_candidates(plan, limit)
        return _deletion_result(query, plan, candidates, errors, {"period": plan.period, "search_text": plan.search_text, "search_terms": list(plan.search_terms), "requires_confirmation": True, "source_count": len(plan.sources), "entity": plan.metadata.get("entity", ""), "deletion_safe": True, "message": "Silmə əməliyyatı icra edilmədi. Əvvəl mənbəni və konkret qeydi dəqiqləşdir."})
    items: list[dict[str, Any]] = []; errors: dict[str, str] = {}; entity = plan.metadata.get("entity", ""); execution_sources = list(plan.sources)
    if plan.intent == "cross_source_search" and entity and "tasks" not in execution_sources: execution_sources.append("tasks")
    for source in execution_sources:
        try:
            if source == "calendar":
                result = get_calendar_events(plan.period or plan.search_text or "today", max(limit, 20) if entity else limit); _append_source(items, source, result, limit, entity, plan.search_terms)
                if result.get("status") == "error": errors[source] = result.get("meta", {}).get("message", "Calendar xətası")
            elif source == "tasks":
                from actions.reminders import get_reminders
                result = get_reminders(plan.period if plan.period else "upcoming", max(limit, 20) if entity else limit, ""); _append_source(items, source, result, limit, entity, plan.search_terms)
                if result.get("status") == "error": errors[source] = result.get("meta", {}).get("message", "Google Tasks xətası")
            elif source == "reminder":
                result = get_memory_reminders(plan.period if plan.period else "upcoming", limit, include_completed=False); _append_source(items, source, result, limit, entity, plan.search_terms)
                if result.get("status") == "error": errors[source] = result.get("meta", {}).get("message", "Xatırlatma yaddaşı xətası")
            elif source == "memory":
                memory_items: dict[str, dict[str, Any]] = {}; memory_terms = plan.search_terms or (plan.search_text,)
                for term in memory_terms:
                    for raw in _memory_items(term, plan.period): memory_items.setdefault(raw["id"], raw)
                for raw in list(memory_items.values())[:limit]:
                    if not entity or _entity_matches(raw, entity) or _matches_search_terms(raw, plan.search_terms): items.append(normalize_item(source, raw, "memory"))
            elif source == "gmail":
                q = plan.search_text
                if plan.period:
                    target = datetime.fromisoformat(_date_query(plan.period)); next_day = target + timedelta(days=1); q = f"after:{target.strftime('%Y/%m/%d')} before:{next_day.strftime('%Y/%m/%d')}"
                result = search_emails(q, limit); _append_source(items, source, result, limit, entity, plan.search_terms)
                if result.get("status") == "error": errors[source] = result.get("meta", {}).get("message", "Gmail xətası")
            elif source == "whatsapp":
                result = read_whatsapp_messages(plan.search_text, deduplicate=True); _append_source(items, source, result, limit, entity, plan.search_terms)
                if result.get("status") == "error": errors[source] = result.get("meta", {}).get("message", "WhatsApp xətası")
        except Exception as exc: errors[source] = str(exc)
    unique: dict[str, dict[str, Any]] = {}
    for item in items: unique.setdefault(item["id"], item)
    ordered = list(unique.values())[: limit * max(1, len(execution_sources))]
    return make_unified_result(query, plan.intent, execution_sources, ordered, errors, {"period": plan.period, "search_text": plan.search_text, "search_terms": list(plan.search_terms), "requires_confirmation": plan.needs_confirmation, "source_count": len(execution_sources), "entity": entity})
