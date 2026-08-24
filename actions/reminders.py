"""Task/agenda adapter with Google Tasks -> EVA memory fallback."""

from __future__ import annotations

from datetime import datetime, time

from core.results import empty, error, success
from integrations.google.tasks import complete_task, create_task, delete_task, list_tasks, resolve_task_list_id, update_task
from memory.memory_manager import load_memory, update_memory, _write_memory


def _parse_due(value: str, all_day: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    if all_day:
        parsed = datetime.combine(parsed.date(), time.min, tzinfo=parsed.tzinfo)
    return parsed.isoformat()


def _structured_task(task: dict, task_list_id: str, source: str = "google_tasks") -> dict:
    return {
        "id": f"task:{task.get('id', '')}",
        "google_task_id": task.get("id", ""),
        "task_list_id": task_list_id,
        "title": task.get("title", ""),
        "due": task.get("due", ""),
        "notes": task.get("notes", ""),
        "status": task.get("status", "needsAction"),
        "updated": task.get("updated", ""),
        "source": source,
    }


def _save_memory_task(title: str, due_iso: str, notes: str) -> dict:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    key = f"{stamp}:{title.strip()}"
    value = {"title": title.strip(), "value": title.strip(), "type": "task", "due": due_iso, "notes": notes, "completed": False}
    update_memory({"agenda": {key: value}})
    return {"id": f"memory:{key}", **value, "source": "memory"}


def get_reminders(query: str = "upcoming", limit: int = 8, list_name: str = "") -> dict:
    try:
        task_list_id = resolve_task_list_id(list_name)
        result_limit = max(1, min(int(limit or 8), 100))
        tasks = list_tasks(task_list_id=task_list_id, max_results=100, show_completed=False)
        normalized_query = str(query or "upcoming").strip().casefold()
        if normalized_query == "today":
            today = datetime.now().date()
            tasks = [task for task in tasks if task.get("due") and datetime.fromisoformat(str(task["due"]).replace("Z", "+00:00")).astimezone().date() == today]
        elif normalized_query not in {"", "upcoming", "next", "qarşıdakı", "qarşıdakı xatırlatmalar"}:
            tasks = [task for task in tasks if normalized_query in str(task.get("title", "")).casefold() or normalized_query in str(task.get("notes", "")).casefold()]
        tasks = tasks[:result_limit]
        payload = {"query": query, "limit": result_limit, "list_name": list_name, "task_list_id": task_list_id}
        if not tasks:
            return empty("task", payload)
        return success("task", [_structured_task(task, task_list_id) for task in tasks], payload)
    except Exception as exc:
        return error("task", str(exc), {"query": query, "limit": limit, "list_name": list_name})


def add_reminder(title: str, due_iso: str = "", notes: str = "", list_name: str = "", priority: str = "", all_day: bool = False, storage: str = "") -> dict:
    title = str(title or "").strip()
    storage = str(storage or "").strip().casefold()
    if not title:
        return error("task", "Task başlığı boş ola bilməz.")
    if not storage:
        return {"type": "task", "status": "needs_input", "query": {"title": title, "due_iso": due_iso}, "data": [], "count": 0, "meta": {"message": "Bunu harada yadda saxlayım: Google Tasks, yoxsa EVA yaddaşında?", "choices": ["google_tasks", "memory"]}}
    if priority:
        return error("task", "Google Tasks priority sahəsini dəstəkləmir; priority göstərmədən yenidən cəhd et.")
    if storage == "memory":
        item = _save_memory_task(title, due_iso, notes)
        return success("task", [item], {"storage": "memory", "requested_storage": storage})
    if storage != "google_tasks":
        return error("task", "Naməlum yaddaş provider-i.")
    try:
        due = _parse_due(due_iso, all_day=bool(all_day))
    except ValueError as exc:
        return error("task", str(exc))
    try:
        task_list_id = resolve_task_list_id(list_name)
        task = create_task(title=title, due_iso=due, notes=str(notes or "").strip(), task_list_id=task_list_id)
        return success("task", [_structured_task(task, task_list_id)], {"storage": "google_tasks", "list_name": list_name, "task_list_id": task_list_id}, {"selected_id": f"task:{task.get('id', '')}"})
    except Exception as exc:
        item = _save_memory_task(title, due_iso, notes)
        return success("task", [item], {"storage": "memory", "requested_storage": "google_tasks"}, {"fallback": True, "reason": "google_tasks_unavailable", "message": "Google Tasks əlçatan deyil; EVA yaddaşında saxlanıldı."})


def update_reminder(task_id: str, title: str = "", due_iso: str = "", notes: str = "", list_name: str = "", all_day: bool = False) -> dict:
    try:
        task_list_id = resolve_task_list_id(list_name)
        due = _parse_due(due_iso, all_day=bool(all_day)) if due_iso else ""
        task = update_task(task_id=task_id, title=title, due_iso=due, notes=notes, task_list_id=task_list_id)
        return success("task", [_structured_task(task, task_list_id)], {"list_name": list_name, "task_list_id": task_list_id}, {"selected_id": f"task:{task.get('id', task_id)}"})
    except Exception as exc:
        return error("task", str(exc))


def complete_reminder(task_id: str, list_name: str = "") -> dict:
    try:
        task_list_id = resolve_task_list_id(list_name)
        task = complete_task(task_id=task_id, task_list_id=task_list_id)
        return success("task", [_structured_task(task, task_list_id)], {"list_name": list_name, "task_list_id": task_list_id}, {"selected_id": f"task:{task.get('id', task_id)}"})
    except Exception as exc:
        return error("task", str(exc))


def delete_reminder(task_id: str, list_name: str = "") -> dict:
    try:
        task_list_id = resolve_task_list_id(list_name)
        delete_task(task_id=task_id, task_list_id=task_list_id)
        return success("task", [], {"list_name": list_name, "task_list_id": task_list_id, "deleted_id": f"task:{task_id}"})
    except Exception as exc:
        return error("task", str(exc))
