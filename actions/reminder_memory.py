"""EVA-nın task və calendar-dan tam ayrı lokal reminder yaddaşı."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from core.results import empty, error, success

BASE_DIR = Path(__file__).resolve().parent.parent
REMINDER_FILE = BASE_DIR / "memory" / "reminders.json"


def _load() -> list[dict]:
    try:
        if not REMINDER_FILE.exists():
            return []
        with REMINDER_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write(items: list[dict]) -> None:
    REMINDER_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = REMINDER_FILE.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2, ensure_ascii=False)
    temporary.replace(REMINDER_FILE)


def _parse_due(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Xatırlatmanın vaxtı göstərilməlidir.")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def _normalize(item: dict) -> dict:
    return {
        "id": str(item.get("id", "")),
        "title": str(item.get("title", "")),
        "due_at": str(item.get("due_at", "")),
        "notes": str(item.get("notes", "")),
        "completed": bool(item.get("completed", False)),
        "created_at": str(item.get("created_at", "")),
        "updated_at": str(item.get("updated_at", "")),
        "source": "eva_memory",
        "type": "reminder",
    }


def add_reminder(title: str, due_at: str, notes: str = "") -> dict:
    title = str(title or "").strip()
    if not title:
        return error("reminder", "Xatırlatma mətni boş ola bilməz.")
    try:
        due = _parse_due(due_at)
    except ValueError as exc:
        return error("reminder", str(exc))

    now = datetime.now().astimezone().isoformat()
    item = {
        "id": f"reminder:{uuid4().hex}",
        "title": title,
        "due_at": due.isoformat(),
        "notes": str(notes or "").strip(),
        "completed": False,
        "created_at": now,
        "updated_at": now,
    }
    items = _load()
    items.append(item)
    _write(items)
    return success("reminder", [_normalize(item)], {"storage": "eva_memory"}, {"selected_id": item["id"]})


def get_reminders(query: str = "today", limit: int = 20, include_completed: bool = False) -> dict:
    normalized = str(query or "today").strip().casefold()
    now = datetime.now().astimezone()
    today = now.date()
    items: list[dict] = []

    for raw in _load():
        item = _normalize(raw)
        if item["completed"] and not include_completed:
            continue
        try:
            due = _parse_due(item["due_at"]).astimezone()
        except ValueError:
            continue
        if normalized in {"today", "bu gün", "bugun"} and due.date() != today:
            continue
        if normalized in {"upcoming", "next", "qarşıdakı"} and due < now:
            continue
        if normalized in {"overdue", "gecikmiş"} and due >= now:
            continue
        items.append(item)

    items.sort(key=lambda item: _parse_due(item["due_at"]).astimezone())
    result_limit = max(1, min(int(limit or 20), 100))
    items = items[:result_limit]
    payload = {"query": query, "limit": result_limit, "include_completed": include_completed, "storage": "eva_memory"}
    if not items:
        return empty("reminder", payload)
    return success("reminder", items, payload)


def complete_reminder(reminder_id: str) -> dict:
    reminder_id = str(reminder_id or "").strip()
    items = _load()
    for item in items:
        if str(item.get("id")) == reminder_id:
            item["completed"] = True
            item["updated_at"] = datetime.now().astimezone().isoformat()
            _write(items)
            return success("reminder", [_normalize(item)], {"storage": "eva_memory"}, {"selected_id": reminder_id})
    return error("reminder", "Xatırlatma tapılmadı.")


def delete_reminder(reminder_id: str) -> dict:
    reminder_id = str(reminder_id or "").strip()
    items = _load()
    remaining = [item for item in items if str(item.get("id")) != reminder_id]
    if len(remaining) == len(items):
        return error("reminder", "Xatırlatma tapılmadı.")
    _write(remaining)
    return success("reminder", [], {"storage": "eva_memory", "deleted_id": reminder_id})


def update_reminder(reminder_id: str, title: str = "", due_at: str = "", notes: str = "") -> dict:
    reminder_id = str(reminder_id or "").strip()
    items = _load()
    for item in items:
        if str(item.get("id")) != reminder_id:
            continue
        if title.strip():
            item["title"] = title.strip()
        if due_at.strip():
            try:
                item["due_at"] = _parse_due(due_at).isoformat()
            except ValueError as exc:
                return error("reminder", str(exc))
        if notes is not None:
            item["notes"] = str(notes).strip()
        item["updated_at"] = datetime.now().astimezone().isoformat()
        _write(items)
        return success("reminder", [_normalize(item)], {"storage": "eva_memory"}, {"selected_id": reminder_id})
    return error("reminder", "Xatırlatma tapılmadı.")
