import json

import pytest

import memory.database as db
from memory.migrate_json import migrate_json_memory
from memory.repository import get_memory


@pytest.fixture
def migration_environment(tmp_path, monkeypatch):
    database_file = tmp_path / "victor.db"
    monkeypatch.setattr(db, "DATABASE_FILE", database_file)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db.initialize_database()

    source = tmp_path / "memory.json"
    return source


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_migration_moves_only_approved_memory_sections(migration_environment):
    source = migration_environment
    data = {
        "identity": {
            "display_name": {"value": "Abdulla"},
            "aliases": {"value": "Abu, Abdulla"},
        },
        "preferences": {"chart_provider": {"value": "tradingview"}},
        "projects": {"sql_memory": {"value": "SQL migration"}},
        "notes": {"aquarium": {"value": "120 liters"}},
        "plans": {"move_to_germany": {"value": "family"}},
        "whatsapp_contacts": {},
        "victor_reminders": {"123": {"title": "Akvarium suyunu dəyişmək"}},
    }
    write_json(source, data)

    report = migrate_json_memory(source)

    assert report["migratable_count"] == 6
    assert report["validated"] is True
    assert get_memory("identity", "display_name")[0]["value"] == {"value": "Abdulla"}
    assert get_memory("preferences", "chart_provider")[0]["value"] == {"value": "tradingview"}
    assert get_memory("projects", "sql_memory")[0]["value"] == {"value": "SQL migration"}
    assert get_memory("notes", "aquarium")[0]["value"] == {"value": "120 liters"}
    assert get_memory("plans", "move_to_germany")[0]["value"] == {"value": "family"}
    assert get_memory("victor_reminders", "123") == []
    assert get_memory("whatsapp_contacts", "anything") == []


def test_migration_is_idempotent(migration_environment):
    source = migration_environment
    data = {"identity": {"display_name": {"value": "Abdulla"}}}
    write_json(source, data)

    migrate_json_memory(source)
    migrate_json_memory(source)

    assert len(get_memory("identity", "display_name")) == 1
    assert get_memory("identity", "display_name")[0]["value"] == {"value": "Abdulla"}


def test_migration_preserves_source_json(migration_environment):
    source = migration_environment
    data = {"notes": {"nested": {"value": {"items": [1, "ə", True]}}}}
    write_json(source, data)
    before = source.read_text(encoding="utf-8")

    migrate_json_memory(source)

    assert source.read_text(encoding="utf-8") == before
    assert get_memory("notes", "nested")[0]["value"] == data["notes"]["nested"]


def test_migration_preserves_nested_leaf_shape(migration_environment):
    source = migration_environment
    value = {"value": "delete_old_on_update", "extra": {"enabled": True}}
    write_json(source, {"preferences": {"calendar": value}})

    migrate_json_memory(source)

    assert get_memory("preferences", "calendar")[0]["value"] == value


def test_migration_dry_run_does_not_write_sql(migration_environment):
    source = migration_environment
    write_json(source, {"identity": {"display_name": {"value": "Abdulla"}}})

    report = migrate_json_memory(source, dry_run=True)

    assert report["migratable_count"] == 1
    assert report["validated"] is False
    assert get_memory("identity", "display_name") == []


def test_migration_missing_source_fails_safely(migration_environment):
    with pytest.raises(FileNotFoundError):
        migrate_json_memory(migration_environment.parent / "missing.json")


def test_migration_invalid_json_fails_safely(migration_environment):
    migration_environment.write_text('{"identity":', encoding="utf-8")

    with pytest.raises(ValueError):
        migrate_json_memory(migration_environment)
