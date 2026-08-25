"""Follow-up mutation payload-larının təhlükəsiz qurulması."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from core.result_resolver import FollowUpAction, ResultResolutionError


@dataclass(frozen=True)
class FollowUpMutation:
    """Resolved follow-up üçün konkret mutation dəyişiklikləri."""

    fields: dict[str, Any]


def build_follow_up_mutation(action: FollowUpAction, *, now: datetime | None = None) -> FollowUpMutation:
    """Follow-up action mətnindən təhlükəsiz mutation payload qurur.

    Hazırda yalnız task üçün ``sabaha keçir`` / ``sabah`` due-date dəyişimini
    dəstəkləyir. Vaxt zonası caller tərəfindən timezone-aware ``now`` ilə
    verildikdə qorunur; naive datetime isə local-time semantikasını saxlayır.
    """
    if action.action != "update":
        raise ResultResolutionError("Mutation yalnız update əməli üçün qurula bilər")

    if not str(action.item.get("id", "")).startswith("task:"):
        raise ResultResolutionError("Follow-up yeniləmə yalnız task üçün dəstəklənir")

    # Action mətni FollowUpAction-da ayrıca saxlanılır. Target item-ə daxili
    # metadata yazmaqla conversation nəticəsini mutasiya etmək lazım deyil.
    normalized = str(action.action_text or "").casefold().strip()
    if "sabah" not in normalized:
        raise ResultResolutionError("Follow-up yeniləmə üçün dəstəklənən dəyişiklik tapılmadı")

    current = now or datetime.now().astimezone()
    tomorrow = (current + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return FollowUpMutation({"due_iso": tomorrow.isoformat()})
