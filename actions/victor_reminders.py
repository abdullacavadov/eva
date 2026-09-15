"""VICTOR-nın Google Tasks-dan ayrı, local memory əsaslı reminder sistemi."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from memory.memory_manager import load_memory, update_memory, delete_memory


def _bucket(memory: dict[str, Any]) -> dict[str, Any]:
    value = memory.get("victor_reminders", {})
    return value if isinstance(value, dict) else {}


def _item(reminder_id: str, value: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"reminder:{reminder_id}", "title": str(value.get("title", "")), "due": str(value.get("due", "")), "notes": str(value.get("notes", "")), "completed": bool(value.get("completed", False)), "source": "victor_memory"}


def get_victor_reminders(query: str = "upcoming", limit: int = 20) -> dict:
    memory = load_memory(); bucket = _bucket(memory); now = datetime.now().astimezone(); normalized = str(query or "upcoming").strip().casefold(); items = [_item(key, value) for key, value in bucket.items() if isinstance(value, dict)]
    if normalized in {"today", "bu gün", "bugün", "bu gun"}: items = [x for x in items if x["due"].startswith(now.date().isoformat())]
    elif normalized in {"upcoming", "next", "qarşıdakı", "qarşıdakı xatırlatmalar"}: items = [x for x in items if not x["completed"]]
    elif normalized in {"completed", "done", "tamamlanan"}: items = [x for x in items if x["completed"]]
    elif normalized not in {"", "all", "bütün"}: items = [x for x in items if normalized in x["title"].casefold() or normalized in x["notes"].casefold()]
    items.sort(key=lambda x: x["due"] or "9999")
    result_limit = max(1, min(int(limit or 20), 100))
    return {"type": "reminder", "status": "success" if items else "empty", "query": {"query": query, "limit": limit}, "data": items[:result_limit], "count": min(len(items), result_limit), "selected": None, "meta": {"storage": "victor_memory"}}


def add_victor_reminder(title: str, due_iso: str = "", notes: str = "") -> dict:
    title = str(title or "").strip()
    if not title: raise ValueError("Reminder başlığı boş ola bilməz.")
    reminder_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    update_memory({"victor_reminders": {reminder_id: {"title": title, "due": str(due_iso or "").strip(), "notes": str(notes or "").strip(), "completed": False}}})
    return {"type": "reminder", "status": "success", "query": {"title": title}, "data": [_item(reminder_id, {"title": title, "due": due_iso, "notes": notes, "completed": False})], "count": 1, "selected": f"reminder:{reminder_id}", "meta": {"storage": "victor_memory"}}


def update_victor_reminder(reminder_id: str, title: str = "", due_iso: str = "", notes: str = "") -> dict:
    key = str(reminder_id or "").removeprefix("reminder:").strip(); memory = load_memory(); bucket = _bucket(memory)
    if key not in bucket: raise ValueError("VICTOR reminder tapılmadı.")
    value = dict(bucket[key]);
    if str(title or "").strip(): value["title"] = str(title).strip()
    if due_iso: value["due"] = str(due_iso).strip()
    if notes: value["notes"] = str(notes).strip()
    update_memory({"victor_reminders": {key: value}})
    return {"type": "reminder", "status": "success", "query": {"reminder_id": reminder_id}, "data": [_item(key, value)], "count": 1, "selected": f"reminder:{key}", "meta": {"storage": "victor_memory"}}


def complete_victor_reminder(reminder_id: str) -> dict:
    key = str(reminder_id or "").removeprefix("reminder:").strip(); memory = load_memory(); bucket = _bucket(memory)
    if key not in bucket: raise ValueError("VICTOR reminder tapılmadı.")
    value = dict(bucket[key]); value["completed"] = True
    update_memory({"victor_reminders": {key: value}})
    return {"type": "reminder", "status": "success", "query": {"reminder_id": reminder_id}, "data": [_item(key, value)], "count": 1, "selected": f"reminder:{key}", "meta": {"storage": "victor_memory"}}


def delete_victor_reminder(reminder_id: str) -> dict:
    key = str(reminder_id or "").removeprefix("reminder:").strip(); memory = load_memory(); bucket = _bucket(memory)
    if key not in bucket: raise ValueError("VICTOR reminder tapılmadı.")
    message = delete_memory("victor_reminders", key)
    if "silindi" not in message:
        raise ValueError("VICTOR reminder tapılmadı.")
    return {"type": "reminder", "status": "success", "query": {"reminder_id": reminder_id}, "data": [], "count": 0, "selected": None, "meta": {"storage": "victor_memory", "deleted_id": f"reminder:{key}"}}
