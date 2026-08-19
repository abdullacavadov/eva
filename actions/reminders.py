"""Google Tasks reminder tool adapter."""

from __future__ import annotations

from datetime import datetime, time

from core.results import empty, error, success
from integrations.google.tasks import create_task, list_tasks, resolve_task_list_id


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


def _structured_task(task: dict, task_list_id: str) -> dict:
    return {
        "id": f"task:{task.get('id', '')}",
        "google_task_id": task.get("id", ""),
        "task_list_id": task_list_id,
        "title": task.get("title", ""),
        "due": task.get("due", ""),
        "notes": task.get("notes", ""),
        "status": task.get("status", "needsAction"),
        "updated": task.get("updated", ""),
    }


def get_reminders(query: str = "upcoming", limit: int = 8, list_name: str = "") -> dict:
    try:
        task_list_id = resolve_task_list_id(list_name)
        result_limit = max(1, min(int(limit or 8), 100))
        tasks = list_tasks(task_list_id=task_list_id, max_results=100, show_completed=False)
        normalized_query = str(query or "upcoming").strip().casefold()
        if normalized_query not in {"", "upcoming", "next", "qarşıdakı", "qarşıdakı xatırlatmalar"}:
            tasks = [task for task in tasks if normalized_query in str(task.get("title", "")).casefold() or normalized_query in str(task.get("notes", "")).casefold()]
        tasks = tasks[:result_limit]
        payload = {"query": query, "limit": result_limit, "list_name": list_name, "task_list_id": task_list_id}
        if not tasks:
            return empty("task", payload)
        return success("task", [_structured_task(task, task_list_id) for task in tasks], payload)
    except Exception as exc:
        return error("task", str(exc), {"query": query, "limit": limit, "list_name": list_name})


def add_reminder(title: str, due_iso: str = "", notes: str = "", list_name: str = "", priority: str = "", all_day: bool = False) -> dict:
    try:
        title = str(title or "").strip()
        if not title:
            return error("task", "Reminder başlığı boş ola bilməz.")
        if priority:
            return error("task", "Google Tasks priority sahəsini dəstəkləmir; priority göstərmədən yenidən cəhd et.")
        due = _parse_due(due_iso, all_day=bool(all_day))
        task_list_id = resolve_task_list_id(list_name)
        task = create_task(title=title, due_iso=due, notes=str(notes or "").strip(), task_list_id=task_list_id)
        return success("task", [_structured_task(task, task_list_id)], {"list_name": list_name, "task_list_id": task_list_id}, {"selected_id": f"task:{task.get('id', '')}"})
    except ValueError as exc:
        return error("task", str(exc))
    except Exception as exc:
        return error("task", str(exc))
