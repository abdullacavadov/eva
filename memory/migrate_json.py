"""VICTOR yaddaş JSON məlumatlarının SQLite-a təhlükəsiz miqrasiyası."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .database import get_connection, initialize_database
from .repository import get_deleted_memory_keys, get_memory, upsert_memory

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MEMORY_FILE = BASE_DIR / "memory" / "memory.json"
MIGRATABLE_CATEGORIES = {"identity", "preferences", "projects", "notes", "plans"}
EXCLUDED_CATEGORIES = {"victor_reminders", "whatsapp_contacts"}
MIGRATION_SOURCE = "json_migration"


def _load_source(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Mənbə yaddaş faylı tapılmadı: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Yaddaş JSON faylı düzgün formatda deyil: {path}") from exc

    if not isinstance(data, dict):
        raise ValueError("Yaddaş JSON faylının kökü obyekt olmalıdır.")
    return data


def _iter_migratable_entries(data: dict[str, Any]):
    for category in MIGRATABLE_CATEGORIES:
        bucket = data.get(category, {})
        if not isinstance(bucket, dict):
            raise ValueError(f"'{category}' bölməsi obyekt olmalıdır.")

        for key, value in bucket.items():
            yield category, str(key), value


def _expected_map(data: dict[str, Any]) -> dict[tuple[str, str], Any]:
    return {
        (category, key): value
        for category, key, value in _iter_migratable_entries(data)
    }


def validate_json_migration(
    data: dict[str, Any],
    *,
    user_id: int = 1,
    skipped_deleted: set[tuple[str, str]] | None = None,
) -> None:
    """JSON mənbəyi ilə SQL yaddaşının uyğunluğunu və dublikatları yoxlayır."""
    expected = _expected_map(data)
    skipped_deleted = skipped_deleted or set()

    for (category, key), expected_value in expected.items():
        if (category, key) in skipped_deleted:
            continue

        rows = get_memory(category=category, key=key, user_id=user_id)
        if len(rows) != 1:
            raise ValueError(
                f"Miqrasiya yoxlaması uğursuz oldu: {category}/{key} üçün {len(rows)} aktiv qeyd var."
            )
        if rows[0]["value"] != expected_value:
            raise ValueError(
                f"Miqrasiya yoxlaması uğursuz oldu: {category}/{key} dəyəri fərqlidir."
            )

    with get_connection() as connection:
        duplicate_rows = connection.execute(
            """
            SELECT category, key, COUNT(*) AS count
            FROM memories
            WHERE user_id = ? AND status = 'active'
              AND category IN ('identity', 'preferences', 'projects', 'notes', 'plans')
            GROUP BY category, key
            HAVING COUNT(*) > 1
            """,
            (user_id,),
        ).fetchall()

    if duplicate_rows:
        duplicates = ", ".join(
            f"{row['category']}/{row['key']} ({row['count']})"
            for row in duplicate_rows
        )
        raise ValueError(f"Miqrasiya yoxlaması uğursuz oldu: dublikatlar var: {duplicates}")


def migrate_json_memory(
    source_path: str | Path = DEFAULT_MEMORY_FILE,
    *,
    user_id: int = 1,
    dry_run: bool = False,
) -> dict[str, Any]:
    """JSON yaddaşını SQL-ə təhlükəsiz və idempotent şəkildə köçürür."""
    source = Path(source_path)
    data = _load_source(source)
    expected = _expected_map(data)

    initialize_database()
    deleted_keys = get_deleted_memory_keys(user_id=user_id)
    migrated_count = 0
    preserved_count = 0
    skipped_deleted_count = 0

    if not dry_run:
        for (category, key), value in expected.items():
            if (category, key) in deleted_keys:
                skipped_deleted_count += 1
                continue

            existing = get_memory(category=category, key=key, user_id=user_id)
            if existing:
                if existing[0]["value"] != value:
                    raise ValueError(
                        f"SQL-də artıq mövcud olan {category}/{key} yaddaşı JSON-dan fərqlidir; "
                        "mövcud SQL məlumatı dəyişdirilmədi."
                    )
                preserved_count += 1
                continue

            upsert_memory(
                category,
                key,
                value,
                user_id=user_id,
                source=MIGRATION_SOURCE,
            )
            migrated_count += 1

        validate_json_migration(
            data,
            user_id=user_id,
            skipped_deleted=deleted_keys & set(expected),
        )

    return {
        "source": str(source),
        "migratable_count": len(expected),
        "migrated_count": migrated_count,
        "preserved_count": preserved_count,
        "skipped_deleted_count": skipped_deleted_count,
        "skipped_categories": sorted(EXCLUDED_CATEGORIES),
        "dry_run": dry_run,
        "validated": not dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="VICTOR yaddaş JSON məlumatlarını SQLite-a köçürür.")
    parser.add_argument("--source", type=Path, default=DEFAULT_MEMORY_FILE)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = migrate_json_memory(args.source, user_id=args.user_id, dry_run=args.dry_run)
    print(f"Miqrasiya ediləcək yaddaş qeydləri: {report['migratable_count']}")
    print(f"Yeni köçürülən: {report['migrated_count']}")
    print(f"SQL-də əvvəlcədən mövcud və qorunan: {report['preserved_count']}")
    print(f"Silinmiş SQL qeydləri səbəbilə keçilən: {report['skipped_deleted_count']}")
    print(f"Keçilməyən bölmələr: {', '.join(report['skipped_categories'])}")
    if report["dry_run"]:
        print("Dry-run tamamlandı; SQL məlumatına dəyişiklik edilmədi.")
    else:
        print("Miqrasiya və SQL yoxlaması uğurla tamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
