from unittest.mock import patch

from actions.contacts import create_contact, delete_contact, update_contact


def test_create_contact_returns_structured_result():
    contact = {
        "display_name": "Test User",
        "resource_name": "people/c123",
        "phones": ["+994501234567"],
    }
    with patch("actions.contacts.create_google_contact", return_value=contact), patch(
        "actions.contacts._reconcile_local_create"
    ):
        result = create_contact("Test User", "0501234567")

    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "contact:people/c123"
    assert result["data"][0]["google_resource_name"] == "people/c123"


def test_update_contact_returns_structured_result():
    contact = {
        "display_name": "Updated User",
        "resource_name": "people/c123",
        "phones": ["+994501234567"],
    }
    with patch("actions.contacts.update_google_contact", return_value=contact), patch(
        "actions.contacts._reconcile_local_update"
    ):
        result = update_contact("people/c123", "Updated User", "0501234567")

    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["data"][0]["display_name"] == "Updated User"
    assert result["data"][0]["google_resource_name"] == "people/c123"


def test_delete_contact_returns_structured_result():
    deletion = {"resource_name": "people/c123", "verification_status": 404}
    with patch("actions.contacts.delete_google_contact", return_value=deletion), patch(
        "actions.contacts._reconcile_local_delete", return_value=True
    ):
        result = delete_contact("people/c123")

    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "contact:people/c123"
    assert result["meta"]["verification_status"] == 404
