import json
from pathlib import Path
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
        return_value="Google Contacts sinxronizasiya edildi: 1 yeni, 0 yenilənmiş, 0 dəyişməyən kontakt. Local-only kontaktlar saxlanıldı.",
    ) as sync:
        response = asyncio.run(
            executor.execute(
                SimpleNamespace(id="contacts-1", name="sync_google_contacts", args={})
            )
        )

    sync.assert_called_once_with()
    assert "1 yeni" in response.response["result"]
