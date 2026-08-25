"""Resolved follow-up əməliyyatlarının təhlükəsiz icrası."""

from __future__ import annotations

from typing import Any, Callable

from core.result_resolver import ResultResolutionError
from core.result_store import ResultStore


class FollowUpExecutionError(RuntimeError):
    """Follow-up əməliyyatının icrası zamanı yaranan xəta."""


def execute_follow_up_dispatch(
    dispatch: Any,
    *,
    complete_task: Callable[..., Any],
    delete_task: Callable[..., Any],
    result_store: ResultStore | None = None,
) -> Any:
    """Dispatch planını uyğun action-a yönləndirir.

    Delete heç vaxt burada confirmation bypass etmir: dispatch planında
    confirmation_required olduqda yalnız plan qaytarılır və action çağırılmır.
    """
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
        raise FollowUpExecutionError("Destructive follow-up üçün confirmation tələb olunur")
    elif dispatch.tool_name is None:
        return {"status": "resolved", "item": dict(dispatch.item)}
    else:
        raise ResultResolutionError("Follow-up üçün dəstəklənməyən icra aləti")

    if result_store is not None and isinstance(result, dict) and {"type", "status", "data"}.issubset(result):
        result_store.save(result)

    return result
