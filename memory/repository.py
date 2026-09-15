"""VICTOR yaddaş məlumatları üçün SQLite repository qatı."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from .database import transaction, utc_now


def _serialize_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _deserialize_value(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _normalize_text(text: str) -> str:
    text = (text or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    replacements = str.maketrans({"ı": "i", "ə": "e", "ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u"})
    text = text.translate(replacements)
    return " ".join(text.split())


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", _normalize_text(text)) if token]


def _value_text(value: Any) -> str:
    if isinstance(value, dict):
        base = value.get("value")
        if base is not None:
            return str(base)
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _recency_score(timestamp: str) -> int:
    """Son yenilənmiş yaddaşlara kiçik, sabit bir üstünlük verir."""
    try:
        updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_days = max(0, (datetime.now(timezone.utc) - updated).total_seconds() / 86400)
        return max(0, int(30 - min(age_days, 30)))
    except (TypeError, ValueError):
        return 0


def _search_score(
    query: str,
    category: str,
    key: str,
    value: Any,
    importance: int,
    updated_at: str,
) -> int:
    normalized_query = _normalize_text(query)
    normalized_category = _normalize_text(category)
    normalized_key = _normalize_text(key)
    normalized_value = _normalize_text(_value_text(value))
    score = max(0, min(int(importance), 100)) + _recency_score(updated_at)

    if normalized_query == normalized_key:
        score += 100
    elif normalized_query in normalized_key:
        score += 60

    if normalized_query == normalized_category:
        score += 80
    elif normalized_query in normalized_category:
        score += 40

    if normalized_query == normalized_value:
        score += 70
    elif normalized_query in normalized_value:
        score += 35

    query_tokens = [token for token in _tokenize(query) if len(token) >= 3]
    entry_tokens = set(_tokenize(f"{category} {key} {_value_text(value)}"))
    matched = sum(1 for token in query_tokens if any(token in entry or entry in token for entry in entry_tokens))
    score += matched * 15
    return score


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


def search_memories(
    query: str,
    *,
    category: str | None = None,
    user_id: int = 1,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """SQL yaddaş qeydlərini uyğunluq, əhəmiyyət və aktuallığa görə sıralayır."""
    query = (query or "").strip()
    if not query or limit <= 0:
        return []

    now = utc_now()
    conditions = [
        "user_id = ?",
        "status = 'active'",
        "(expires_at IS NULL OR expires_at > ?)",
    ]
    params: list[Any] = [user_id, now]

    if category:
        conditions.append("category = ?")
        params.append(category)

    with transaction() as connection:
        rows = connection.execute(
            f"""
            SELECT id, user_id, type, category, key, value, source,
                   confidence, importance, status, created_at, updated_at,
                   last_accessed_at, expires_at
            FROM memories
            WHERE {' AND '.join(conditions)}
            """,
            params,
        ).fetchall()

        results = []
        for row in rows:
            value = _deserialize_value(row["value"])
            score = _search_score(
                query,
                row["category"],
                row["key"],
                value,
                row["importance"],
                row["updated_at"],
            )
            normalized_query = _normalize_text(query)
            searchable = _normalize_text(
                f"{row['category']} {row['key']} {_value_text(value)}"
            )
            if normalized_query not in searchable and not any(
                token in searchable for token in _tokenize(query) if len(token) >= 3
            ):
                continue

            results.append({**dict(row), "value": value, "score": score})

        results.sort(key=lambda item: (item["score"], item["importance"], item["updated_at"]), reverse=True)
        results = results[:limit]

        if results:
            accessed_at = utc_now()
            ids = [item["id"] for item in results]
            placeholders = ",".join("?" for _ in ids)
            connection.execute(
                f"UPDATE memories SET last_accessed_at = ? WHERE id IN ({placeholders})",
                [accessed_at, *ids],
            )
            for item in results:
                item["last_accessed_at"] = accessed_at

        return results


def get_deleted_memory_keys(*, user_id: int = 1) -> set[tuple[str, str]]:
    """JSON fallback-dan gizlədilməli SQL soft-delete qeydlərinin açarlarını qaytarır."""
    with transaction() as connection:
        rows = connection.execute(
            """
            SELECT category, key
            FROM memories
            WHERE user_id = ? AND status = 'deleted'
            """,
            (user_id,),
        ).fetchall()
    return {(str(row["category"]), str(row["key"])) for row in rows}


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
