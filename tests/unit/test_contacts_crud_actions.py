from unittest.mock import patch

import pytest

from actions.contacts import create_contact, delete_contact, update_contact


def test_create_contact_normalizes_phone_before_google_write():
    with (
        patch("actions.contacts.create_google_contact", return_value={"display_name": "Test", "resource_name": "people/c1", "phones": ["+994501234567"]}) as mock_create,
        patch("actions.contacts._reconcile_local_create") as reconcile,
    ):
        result = create_contact("Test", "0501234567")
    mock_create.assert_called_once_with("Test", ["+994501234567"])
    reconcile.assert_called_once()
    assert result["status"] == "success"
    assert result["data"][0]["google_resource_name"] == "people/c1"


def test_update_contact_requires_valid_phone():
    with pytest.raises(ValueError, match="Telefon nömrəsi"):
        update_contact("people/c1", "Test", "123")


def test_update_contact_passes_resource_name_and_reconciles_local_state():
    google_result = {"display_name": "Updated", "resource_name": "people/c1", "phones": ["+994559041494"]}
    with patch("actions.contacts.update_google_contact", return_value=google_result) as mock_update, patch("actions.contacts._reconcile_local_update") as reconcile:
        result = update_contact("people/c1", "Updated", "+994559041494")
    mock_update.assert_called_once_with("people/c1", "Updated", ["+994559041494"])
    reconcile.assert_called_once_with(google_result)
    assert result["status"] == "success"
    assert result["data"][0]["display_name"] == "Updated"


def test_delete_contact_reconciles_local_state_after_verified_google_delete():
    google_result = {"resource_name": "people/c1", "verification_status": 404, "deleted": True}
    with patch("actions.contacts.delete_google_contact", return_value=google_result) as mock_delete, patch("actions.contacts._reconcile_local_delete", return_value=True) as reconcile:
        result = delete_contact("people/c1")
    mock_delete.assert_called_once_with("people/c1")
    reconcile.assert_called_once_with("people/c1")
    assert result["status"] == "success"
    assert result["meta"]["verification_status"] == 404
    assert result["meta"]["local_removed"] is True


def test_create_contact_reports_partial_success_when_local_reconciliation_fails():
    google_result = {"display_name": "Test", "resource_name": "people/c1", "phones": ["+994501234567"]}
    with patch("actions.contacts.create_google_contact", return_value=google_result), patch("actions.contacts._reconcile_local_create", side_effect=OSError("disk failed")):
        result = create_contact("Test", "0501234567")
    assert result["status"] == "partial"
    assert result["data"][0]["google_resource_name"] == "people/c1"
    assert result["meta"]["local_sync_error"] == "disk failed"
