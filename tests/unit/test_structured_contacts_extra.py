from unittest.mock import patch

from actions.contacts import delete_contact, update_contact


def test_update_contact_structured_identity():
    contact = {"display_name": "Updated User", "resource_name": "people/c123", "phones": ["+994501234567"]}
    with patch("actions.contacts.update_google_contact", return_value=contact), patch("actions.contacts._reconcile_local_update"):
        result = update_contact("people/c123", "Updated User", "0501234567")
    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["data"][0]["google_resource_name"] == "people/c123"


def test_delete_contact_structured_identity():
    deletion = {"resource_name": "people/c123", "verification_status": 404}
    with patch("actions.contacts.delete_google_contact", return_value=deletion), patch("actions.contacts._reconcile_local_delete", return_value=True):
        result = delete_contact("people/c123")
    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["data"][0]["id"] == "contact:people/c123"
    assert result["meta"]["verification_status"] == 404
