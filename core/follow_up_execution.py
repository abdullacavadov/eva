"""Resolved follow-up əməliyyatlarının təhlükəsiz icrası."""

from __future__ import annotations

from typing import Any, Callable

from actions.reminders import complete_reminder, delete_reminder
from core.result_resolver import ResultResolutionError
from core.result_store import ResultStore


class FollowUpExecutionError(RuntimeError):
    """Follow-up əməliyyatının icrası zamanı yaranan xəta."""


def execute_follow_up_dispatch(
    dispatch: Any,
    *,
    complete_task: Callable[..., Any] | None = None,
    delete_task: Callable[..., Any] | None = None,
    result_store: ResultStore | None = None,
) -> Any:
    """Dispatch planını mövcud action layer-ə yönləndirir.

    ``complete_task`` verilmədikdə EVA-nın real ``complete_reminder`` action-ı
    istifadə olunur. Delete dispatch-i isə confirmation tələb etdiyi üçün
    burada heç vaxt icra edilmir.
    """
    complete_task = complete_task or complete_reminder
    delete_task = delete_task or delete_reminder

    if dispatch.confirmation_required:
        return {
            "status": "confirmation_required",
            "action": dispatch.tool_name,
            "args": dict(dispatch.args),
            "item": dict(dispatch.item),
        }

    if dispatch.tool_name == "complete_reminder":
        result = complete_task(**dispatch.args)
    elif dispatch.tool_name == "delete_reminder":
        # Defensive guard: a delete plan without the confirmation flag must
        # fail closed instead of accidentally mutating external state.
        delete_task  # intentionally unused; deletion is never auto-dispatched
        raise FollowUpExecutionError("Destructive follow-up üçün confirmation tələb olunur")
    elif dispatch.tool_name is None:
        return {"status": "resolved", "item": dict(dispatch.item)}
    else:
        raise ResultResolutionError("Follow-up üçün dəstəklənən icra aləti yoxdur")

    if result_store is not None and isinstance(result, dict) and {"type", "status", "data"}.issubset(result):
        result_store.save(result)

    return result
