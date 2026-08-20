from unittest.mock import patch

from actions.contacts import create_contact


def test_create_contact_result_contract():
    contact = {"display_name": "Test User", "resource_name": "people/c123", "phones": ["+994501234567"]}
    with patch("actions.contacts.create_google_contact", return_value=contact), patch("actions.contacts._reconcile_local_create"):
        result = create_contact("Test User", "0501234567")
    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"][0]["id"] == "contact:people/c123"
