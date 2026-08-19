import json
from unittest.mock import MagicMock, patch

from actions import contacts


def _write_phone_book(monkeypatch, tmp_path, data):
    path = tmp_path / "phone_book.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(contacts, "PHONEBOOK_FILE", path)
    return path


def test_sync_adds_new_google_contact(monkeypatch, tmp_path):
    path = _write_phone_book(monkeypatch, tmp_path, {})
    monkeypatch.setattr(
        contacts,
        "get_google_contacts",
        lambda: [
            {
                "resource_name": "people/c123",
                "display_name": "Əhməd",
                "phones": ["+994501234567"],
            }
        ],
    )

    result = contacts.sync_google_contacts()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "Əhməd".casefold().replace("ə", "e") in " ".join(data.keys()).casefold().replace("ə", "e")
    entry = next(iter(data.values()))
    assert entry["display_name"] == "Əhməd"
    assert entry["value"] == "+994501234567"
    assert entry["google_resource_name"] == "people/c123"
    assert "1 yeni" in result


def test_sync_keeps_unchanged_contact_untouched(monkeypatch, tmp_path):
    original = {
        "ehmed": {
            "display_name": "Əhməd",
            "value": "+994501234567",
            "aliases": ["Ami"],
        }
    }
    path = _write_phone_book(monkeypatch, tmp_path, original)
    monkeypatch.setattr(
        contacts,
        "get_google_contacts",
        lambda: [
            {
                "resource_name": "people/c123",
                "display_name": "Əhməd",
                "phones": ["+994501234567"],
            }
        ],
    )

    contacts.sync_google_contacts()

    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_sync_updates_changed_name(monkeypatch, tmp_path):
    original = {"ehmed": {"display_name": "Əhməd", "value": "+994501234567"}}
    path = _write_phone_book(monkeypatch, tmp_path, original)
    monkeypatch.setattr(
        contacts,
        "get_google_contacts",
        lambda: [
            {
                "resource_name": "people/c123",
                "display_name": "Əhməd Cavadov",
                "phones": ["+994501234567"],
            }
        ],
    )

    contacts.sync_google_contacts()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ehmed"]["display_name"] == "Əhməd Cavadov"
    assert data["ehmed"]["value"] == "+994501234567"


def test_sync_updates_changed_phone_by_name(monkeypatch, tmp_path):
    original = {"ehmed": {"display_name": "Əhməd", "value": "+994501234567"}}
    path = _write_phone_book(monkeypatch, tmp_path, original)
    monkeypatch.setattr(
        contacts,
        "get_google_contacts",
        lambda: [
            {
                "resource_name": "people/c123",
                "display_name": "Əhməd",
                "phones": ["+994559041494"],
            }
        ],
    )

    contacts.sync_google_contacts()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ehmed"]["value"] == "+994559041494"


def test_sync_preserves_local_only_contacts(monkeypatch, tmp_path):
    original = {
        "local": {"display_name": "Local", "value": "+994501111111"},
    }
    path = _write_phone_book(monkeypatch, tmp_path, original)
    monkeypatch.setattr(contacts, "get_google_contacts", lambda: [])

    contacts.sync_google_contacts()

    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_sync_removes_stale_google_managed_contact(monkeypatch, tmp_path):
    original = {
        "google_contact": {
            "display_name": "Google Contact",
            "value": "+994501111111",
            "google_resource_name": "people/deleted",
        },
        "local": {"display_name": "Local", "value": "+994502222222"},
    }
    path = _write_phone_book(monkeypatch, tmp_path, original)
    monkeypatch.setattr(contacts, "get_google_contacts", lambda: [])

    result = contacts.sync_google_contacts()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "google_contact" not in data
    assert "local" in data
    assert "1 silinmiş" in result


def test_reconcile_local_create_persists_google_identity(monkeypatch, tmp_path):
    path = _write_phone_book(monkeypatch, tmp_path, {})

    contacts._reconcile_local_create(
        {
            "display_name": "Test",
            "resource_name": "people/c1",
            "phones": ["+994501234567"],
        }
    )

    data = json.loads(path.read_text(encoding="utf-8"))
    entry = next(iter(data.values()))
    assert entry["display_name"] == "Test"
    assert entry["value"] == "+994501234567"
    assert entry["google_resource_name"] == "people/c1"


def test_reconcile_local_update_matches_existing_google_identity(monkeypatch, tmp_path):
    original = {
        "test": {
            "display_name": "Old",
            "value": "+994501234567",
            "google_resource_name": "people/c1",
            "aliases": ["T"],
        }
    }
    path = _write_phone_book(monkeypatch, tmp_path, original)

    contacts._reconcile_local_update(
        {
            "display_name": "Updated",
            "resource_name": "people/c1",
            "phones": ["+994559041494"],
        }
    )

    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(data) == ["test"]
    assert data["test"]["display_name"] == "Updated"
    assert data["test"]["value"] == "+994559041494"
    assert data["test"]["google_resource_name"] == "people/c1"
    assert data["test"]["aliases"] == ["T"]


def test_reconcile_local_delete_removes_only_matching_google_contact(monkeypatch, tmp_path):
    original = {
        "google": {
            "display_name": "Google",
            "value": "+994501111111",
            "google_resource_name": "people/c1",
        },
        "local": {"display_name": "Local", "value": "+994502222222"},
    }
    path = _write_phone_book(monkeypatch, tmp_path, original)

    removed = contacts._reconcile_local_delete("people/c1")

    assert removed is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "google" not in data
    assert "local" in data


def test_sync_does_not_corrupt_phone_book_on_google_error(monkeypatch, tmp_path):
    original = {"local": {"display_name": "Local", "value": "+994501111111"}}
    path = _write_phone_book(monkeypatch, tmp_path, original)
    monkeypatch.setattr(
        contacts,
        "get_google_contacts",
        MagicMock(side_effect=RuntimeError("OAuth failed")),
    )

    result = contacts.sync_google_contacts()

    assert "alınmadı" in result
    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_sync_deduplicates_google_contacts_by_phone(monkeypatch, tmp_path):
    path = _write_phone_book(monkeypatch, tmp_path, {})
    monkeypatch.setattr(
        contacts,
        "get_google_contacts",
        lambda: [
            {"resource_name": "people/1", "display_name": "Test", "phones": ["+994501234567"]},
            {"resource_name": "people/2", "display_name": "Test 2", "phones": ["+994501234567"]},
        ],
    )

    contacts.sync_google_contacts()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_tool_executor_dispatches_contact_sync():
    import asyncio
    from types import SimpleNamespace

    from core.tool_executor import ToolExecutor

    ui = MagicMock()
    ui.muted = False
    executor = ToolExecutor(ui, MagicMock(), MagicMock(), MagicMock())

    with patch(
        "core.tool_executor.sync_google_contacts",
        return_value="Google Contacts sinxronizasiya edildi: 1 yeni, 0 yenilənmiş, 0 silinmiş, 0 dəyişməyən kontakt. Local-only kontaktlar saxlanıldı.",
    ) as sync:
        response = asyncio.run(
            executor.execute(
                SimpleNamespace(id="contacts-1", name="sync_google_contacts", args={})
            )
        )

    sync.assert_called_once_with()
    assert "1 yeni" in response.response["result"]
