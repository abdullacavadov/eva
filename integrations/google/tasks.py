from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from googleapiclient.discovery import build

from integrations.google.auth import get_google_credentials


def get_tasks_service():
    return build(
        "tasks",
        "v1",
        credentials=get_google_credentials(),
    )


def list_task_lists() -> list[dict[str, Any]]:
    service = get_tasks_service()
    result: list[dict[str, Any]] = []
    page_token = None

    while True:
        request = service.tasklists().list()
        if page_token:
            request = service.tasklists().list(pageToken=page_token)
        response = request.execute()
        result.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return result


def resolve_task_list_id(list_name: str = "") -> str:
    name = str(list_name or "").strip()
    if not name:
        return "@default"

    matches = [
        item
        for item in list_task_lists()
        if str(item.get("title", "")).strip().casefold() == name.casefold()
    ]

    if len(matches) == 1:
        return str(matches[0]["id"])
    if len(matches) > 1:
        raise ValueError(f"'{name}' adı ilə birdən çox task list tapıldı.")
    raise ValueError(f"Task list tapılmadı: {name}")


def list_tasks(
    task_list_id: str = "@default",
    max_results: int = 20,
    show_completed: bool = False,
) -> list[dict[str, Any]]:
    service = get_tasks_service()
    target = max(1, min(int(max_results or 20), 100))
    result: list[dict[str, Any]] = []
    page_token = None

    while len(result) < target:
        kwargs = {
            "tasklist": task_list_id,
            "maxResults": min(100, target - len(result)),
            "showCompleted": show_completed,
            "showHidden": False,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.tasks().list(**kwargs).execute()
        result.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return result[:target]


def create_task(
    title: str,
    due_iso: str = "",
    notes: str = "",
    task_list_id: str = "@default",
) -> dict[str, Any]:
    service = get_tasks_service()
    body: dict[str, Any] = {"title": title}

    if notes:
        body["notes"] = notes

    if due_iso:
        body["due"] = _normalize_due(due_iso)

    return (
        service.tasks()
        .insert(tasklist=task_list_id, body=body)
        .execute()
    )


def update_task(
    task_id: str,
    title: str = "",
    due_iso: str = "",
    notes: str = "",
    task_list_id: str = "@default",
) -> dict[str, Any]:
    task_id = str(task_id or "").strip()
    if not task_id:
        raise ValueError("Task ID tələb olunur.")

    service = get_tasks_service()
    body: dict[str, Any] = {}
    if title.strip():
        body["title"] = title.strip()
    if notes:
        body["notes"] = notes
    if due_iso:
        body["due"] = _normalize_due(due_iso)

    if not body:
        raise ValueError("Yeniləmək üçün ən azı title, notes və ya due_iso verilməlidir.")

    return (
        service.tasks()
        .patch(tasklist=task_list_id, task=task_id, body=body)
        .execute()
    )


def complete_task(task_id: str, task_list_id: str = "@default") -> dict[str, Any]:
    task_id = str(task_id or "").strip()
    if not task_id:
        raise ValueError("Task ID tələb olunur.")
    service = get_tasks_service()
    return (
        service.tasks()
        .patch(
            tasklist=task_list_id,
            task=task_id,
            body={"status": "completed"},
        )
        .execute()
    )


def delete_task(task_id: str, task_list_id: str = "@default") -> None:
    task_id = str(task_id or "").strip()
    if not task_id:
        raise ValueError("Task ID tələb olunur.")
    service = get_tasks_service()
    service.tasks().delete(tasklist=task_list_id, task=task_id).execute()


def _normalize_due(value: str) -> str:
    parsed = datetime.fromisoformat(
        str(value).strip().replace("Z", "+00:00")
    )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
