from unittest.mock import patch

from actions.contacts import create_contact


def test_contacts_structured_contract_for_ci():
    contact = {"display_name": "CI User", "resource_name": "people/ci", "phones": ["+994501234567"]}
    with patch("actions.contacts.create_google_contact", return_value=contact), patch("actions.contacts._reconcile_local_create"):
        result = create_contact("CI User", "0501234567")
    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["data"][0]["google_resource_name"] == "people/ci"
