"""VICTOR SQLite verilənlər bazası bağlantısı və ilkinləşdirməsi."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_FILE = DATA_DIR / "victor.db"
SCHEMA_FILE = Path(__file__).resolve().with_name("schema.sql")


def utc_now() -> str:
    """Cari UTC vaxtını ISO 8601 formatında qaytarır."""
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """VICTOR SQLite bazasına yeni bağlantı açır."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database() -> None:
    """SQLite bazasını idempotent şəkildə ilkinləşdirir."""
    schema = SCHEMA_FILE.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)
        connection.execute(
            """
            INSERT OR IGNORE INTO schema_version(version, applied_at)
            VALUES (?, ?)
            """,
            (1, utc_now()),
        )


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Bir əməliyyat üçün transaction idarə edir."""
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
