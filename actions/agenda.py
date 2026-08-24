"""Unified agenda orchestration for Google Tasks, Calendar and local memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.results import empty, error, success
from memory.memory_manager import load_memory, update_memory, _write_memory
from actions.calendar import get_calendar_events
from actions.reminders import get_reminders, add_reminder, delete_reminder


def _memory_items() -> list[dict[str, Any]]:
    memory = load_memory()
    bucket = memory.get("agenda", {})
    if not isinstance(bucket, dict):
        return []
    items = []
    for key, value in bucket.items():
        if not isinstance(value, dict):
            continue
        items.append({
            "id": f"memory:{key}",
            "title": str(value.get("title", value.get("value", key))),
            "type": value.get("type", "note"),
            "due": value.get("due", ""),
            "notes": value.get("notes", ""),
            "completed": bool(value.get("completed", False)),
            "source": "memory",
        })
    return items


def _memory_key(title: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{stamp}:{title.strip()}"


def _today_memory(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.now().astimezone().date().isoformat()
    result = []
    for item in items:
        due = str(item.get("due", ""))
        if due.startswith(today):
            result.append(item)
    return result


def get_daily_agenda(limit: int = 20) -> dict:
    result_limit = max(1, min(int(limit or 20), 100))
    sources: dict[str, Any] = {}
    errors: dict[str, str] = {}

    try:
        calendar_result = get_calendar_events("today", result_limit)
        sources["calendar"] = calendar_result.get("data", [])
        if calendar_result.get("status") == "error":
            errors["calendar"] = calendar_result.get("meta", {}).get("message", "Calendar xətası")
    except Exception as exc:
        sources["calendar"] = []
        errors["calendar"] = str(exc)

    try:
        task_result = get_reminders("today", result_limit, "")
        sources["tasks"] = task_result.get("data", [])
        if task_result.get("status") == "error":
            errors["tasks"] = task_result.get("meta", {}).get("message", "Tasks xətası")
    except Exception as exc:
        sources["tasks"] = []
        errors["tasks"] = str(exc)

    sources["memory"] = _today_memory(_memory_items())
    data = {
        "date": datetime.now().astimezone().date().isoformat(),
        "calendar": sources["calendar"],
        "tasks": sources["tasks"],
        "todo": [],
        "memory": sources["memory"],
        "errors": errors,
    }
    combined = sources["calendar"] + sources["tasks"] + sources["memory"]
    if not combined and errors:
        return error("daily_agenda", "Gündəlik məlumatların heç biri oxuna bilmədi.", {"date": data["date"], "errors": errors})
    if not combined:
        return empty("daily_agenda", {"date": data["date"], "sources": ["calendar", "tasks", "memory"], "errors": errors})
    return success("daily_agenda", data, {"date": data["date"], "sources": ["calendar", "tasks", "memory"], "errors": errors})


def add_agenda_item(title: str, item_type: str = "task", storage: str = "", due_iso: str = "", notes: str = "") -> dict:
    title = str(title or "").strip()
    storage = str(storage or "").strip().casefold()
    item_type = str(item_type or "task").strip().casefold()
    if not title:
        return error("agenda_item", "Başlıq boş ola bilməz.")
    if storage not in {"google_tasks", "memory"}:
        return {
            "type": "agenda_item",
            "status": "needs_input",
            "query": {"title": title, "item_type": item_type, "due_iso": due_iso},
            "data": [],
            "count": 0,
            "meta": {"message": "Bunu harada yadda saxlayım: Google Tasks, Microsoft To Do, yoxsa EVA yaddaşında?", "choices": ["google_tasks", "microsoft_todo", "memory"]},
        }

    if storage == "google_tasks":
        if item_type == "note":
            return error("agenda_item", "Google Tasks qeyd üçün nəzərdə tutulmayıb; qeyd üçün memory seç.")
        return add_reminder(title, due_iso, notes)

    key = _memory_key(title)
    update_memory({"agenda": {key: {"title": title, "value": title, "type": item_type, "due": due_iso, "notes": notes, "completed": False}}})
    item = {"id": f"memory:{key}", "title": title, "type": item_type, "due": due_iso, "notes": notes, "completed": False, "source": "memory"}
    return success("agenda_item", [item], {"storage": "memory"}, {"selected_id": item["id"]})


def delete_agenda_item(match_text: str = "", storage: str = "", confirm: bool = False) -> dict:
    needle = str(match_text or "").strip().casefold()
    storage = str(storage or "").strip().casefold()
    if not needle:
        return error("agenda_item", "Silinəcək task və ya qeyd göstərilməlidir.")

    candidates: list[dict[str, Any]] = []
    if storage in {"", "memory"}:
        candidates.extend([item for item in _memory_items() if needle in item["title"].casefold()])
    if storage in {"", "google_tasks"}:
        try:
            task_result = get_reminders(needle, 100, "")
            candidates.extend(task_result.get("data", []))
        except Exception:
            pass

    if not candidates:
        return empty("agenda_item", {"match_text": match_text, "storage": storage})
    if len(candidates) > 1 or not confirm:
        return {
            "type": "agenda_item",
            "status": "needs_confirmation",
            "query": {"match_text": match_text, "storage": storage},
            "data": candidates[:10],
            "count": len(candidates),
            "meta": {"message": "Bu silmə əməliyyatıdır. Hansı qeydi silmək istədiyini və təsdiqini dəqiqləşdir.", "confirmation_required": True},
        }

    item = candidates[0]
    if item.get("source") == "memory":
        key = str(item["id"])[len("memory:"):]
        memory = load_memory()
        bucket = memory.get("agenda", {})
        if isinstance(bucket, dict):
            bucket.pop(key, None)
            if not bucket:
                memory.pop("agenda", None)
            _write_memory(memory)
        return success("agenda_item", [], {"deleted_id": item["id"], "storage": "memory"})

    task_id = item.get("google_task_id", "")
    return delete_reminder(task_id, "")
