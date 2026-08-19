"""Google Tasks reminder tool adapter."""

from __future__ import annotations

from datetime import datetime, time

from integrations.google.tasks import (
    create_task,
    list_tasks,
    resolve_task_list_id,
)


def _parse_due(value: str, all_day: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))

    if all_day:
        parsed = datetime.combine(
            parsed.date(),
            time.min,
            tzinfo=parsed.tzinfo,
        )

    return parsed.isoformat()


def _format_task(task: dict) -> str:
    title = task.get("title") or "(Adsız reminder)"
    due = task.get("due", "")
    notes = task.get("notes", "")

    result = f"- {title}"
    if due:
        result += f" — {due}"
    if notes:
        result += f" — {notes}"
    return result


def get_reminders(
    query: str = "upcoming",
    limit: int = 8,
    list_name: str = "",
) -> str:
    try:
        task_list_id = resolve_task_list_id(list_name)
        tasks = list_tasks(
            task_list_id=task_list_id,
            max_results=max(1, min(int(limit or 8), 100)),
            show_completed=False,
        )

        normalized_query = str(query or "upcoming").strip().casefold()
        if normalized_query not in {"", "upcoming", "next", "qarşıdakı", "qarşıdakı xatırlatmalar"}:
            tasks = [
                task
                for task in tasks
                if normalized_query in str(task.get("title", "")).casefold()
                or normalized_query in str(task.get("notes", "")).casefold()
            ]

        if not tasks:
            return "Göstərilən meyarlara uyğun reminder tapılmadı."

        lines = [f"Google Tasks — {len(tasks)} reminder:"]
        lines.extend(_format_task(task) for task in tasks)
        return "\n".join(lines)

    except Exception as exc:
        return f"Google Tasks reminder-ları oxunarkən xəta baş verdi: {exc}"


def add_reminder(
    title: str,
    due_iso: str = "",
    notes: str = "",
    list_name: str = "",
    priority: str = "",
    all_day: bool = False,
) -> str:
    try:
        title = str(title or "").strip()
        if not title:
            return "Reminder başlığı boş ola bilməz."

        if priority:
            return "Google Tasks priority sahəsini dəstəkləmir; priority göstərmədən yenidən cəhd et."

        due = _parse_due(due_iso, all_day=bool(all_day))
        task_list_id = resolve_task_list_id(list_name)
        task = create_task(
            title=title,
            due_iso=due,
            notes=str(notes or "").strip(),
            task_list_id=task_list_id,
        )

        return f"Google Tasks-a '{task.get('title', title)}' reminder-i əlavə edildi."

    except ValueError as exc:
        return f"Reminder məlumatı yanlışdır: {exc}"
    except Exception as exc:
        return f"Google Tasks reminder-i yaradılarkən xəta baş verdi: {exc}"
