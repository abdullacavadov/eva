from memory.database import initialize_database
from memory.repository import delete_memory, get_memory, upsert_memory


def test_memory_repository_crud(tmp_path, monkeypatch):
    import memory.database as db

    database_file = tmp_path / "victor.db"
    monkeypatch.setattr(db, "DATABASE_FILE", database_file)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)

    initialize_database()

    memory_id = upsert_memory("profile", "name", "Abdulla")
    assert memory_id > 0
    assert get_memory("profile", "name")[0]["value"] == "Abdulla"

    upsert_memory("profile", "name", "Victor")
    rows = get_memory("profile", "name")
    assert len(rows) == 1
    assert rows[0]["value"] == "Victor"

    assert delete_memory("profile", "name") is True
    assert get_memory("profile", "name") == []


def test_memory_repository_preserves_structured_values(tmp_path, monkeypatch):
    import memory.database as db

    database_file = tmp_path / "victor.db"
    monkeypatch.setattr(db, "DATABASE_FILE", database_file)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)

    initialize_database()
    value = {"display_name": "Əhməd", "value": "+994501234567", "aliases": ["Əmi", "Ahmed"]}

    upsert_memory("whatsapp_contacts", "ahmed", value)
    rows = get_memory("whatsapp_contacts", "ahmed")

    assert rows[0]["value"] == value


def test_deleted_memory_can_be_recreated(tmp_path, monkeypatch):
    import memory.database as db

    database_file = tmp_path / "victor.db"
    monkeypatch.setattr(db, "DATABASE_FILE", database_file)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)

    initialize_database()
    first_id = upsert_memory("profile", "city", "Bakı")
    assert delete_memory("profile", "city") is True

    second_id = upsert_memory("profile", "city", "Gəncə")
    assert second_id != first_id
    assert get_memory("profile", "city")[0]["value"] == "Gəncə"
