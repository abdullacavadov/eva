"""VICTOR yaddaş məlumatları üçün SQLite repository qatı."""

from __future__ import annotations

import json
from typing import Any

from .database import transaction, utc_now


def _serialize_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _deserialize_value(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def upsert_memory(
    category: str,
    key: str,
    value: Any,
    *,
    user_id: int = 1,
    source: str = "user_explicit",
    confidence: float | None = None,
    importance: int = 0,
) -> int:
    """Yaddaş qeydini yaradır və ya mövcud qeydi yeniləyir."""
    now = utc_now()
    serialized = _serialize_value(value)

    with transaction() as connection:
        row = connection.execute(
            """
            SELECT id FROM memories
            WHERE user_id = ? AND category = ? AND key = ? AND status = 'active'
            LIMIT 1
            """,
            (user_id, category, key),
        ).fetchone()

        if row:
            connection.execute(
                """
                UPDATE memories
                SET value = ?, source = ?, confidence = ?, importance = ?, updated_at = ?
                WHERE id = ?
                """,
                (serialized, source, confidence, importance, now, row["id"]),
            )
            return int(row["id"])

        cursor = connection.execute(
            """
            INSERT INTO memories
                (user_id, type, category, key, value, source, confidence,
                 importance, status, created_at, updated_at)
            VALUES (?, 'memory', ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (user_id, category, key, serialized, source, confidence, importance, now, now),
        )
        return int(cursor.lastrowid)


def get_memory(
    category: str | None = None,
    key: str | None = None,
    *,
    user_id: int = 1,
) -> list[dict[str, Any]]:
    """Aktiv yaddaş qeydlərini category/key üzrə qaytarır."""
    conditions = ["user_id = ?", "status = 'active'"]
    params: list[Any] = [user_id]

    if category:
        conditions.append("category = ?")
        params.append(category)
    if key:
        conditions.append("key = ?")
        params.append(key)

    with transaction() as connection:
        rows = connection.execute(
            f"""
            SELECT id, user_id, type, category, key, value, source,
                   confidence, importance, status, created_at, updated_at,
                   last_accessed_at, expires_at
            FROM memories
            WHERE {' AND '.join(conditions)}
            ORDER BY importance DESC, updated_at DESC
            """,
            params,
        ).fetchall()

        return [
            {
                **dict(row),
                "value": _deserialize_value(row["value"]),
            }
            for row in rows
        ]


def delete_memory(category: str, key: str, *, user_id: int = 1) -> bool:
    """Aktiv yaddaş qeydini fiziki silmədən deleted statusuna keçirir."""
    with transaction() as connection:
        cursor = connection.execute(
            """
            UPDATE memories
            SET status = 'deleted', updated_at = ?
            WHERE user_id = ? AND category = ? AND key = ? AND status = 'active'
            """,
            (utc_now(), user_id, category, key),
        )
        return cursor.rowcount > 0
