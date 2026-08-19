from unittest.mock import patch

import pytest

from actions.contacts import create_contact, delete_contact, update_contact


def test_create_contact_normalizes_phone_before_google_write():
    with (
        patch(
            "actions.contacts.create_google_contact",
            return_value={
                "display_name": "Test",
                "resource_name": "people/c1",
                "phones": ["+994501234567"],
            },
        ) as mock_create,
        patch("actions.contacts._reconcile_local_create") as reconcile,
    ):
        result = create_contact("Test", "0501234567")

    mock_create.assert_called_once_with("Test", ["+994501234567"])
    reconcile.assert_called_once_with(
        {
            "display_name": "Test",
            "resource_name": "people/c1",
            "phones": ["+994501234567"],
        }
    )
    assert "people/c1" in result
    assert "local phone book" in result


def test_update_contact_requires_valid_phone():
    with pytest.raises(ValueError, match="Telefon nömrəsi"):
        update_contact("people/c1", "Test", "123")


def test_update_contact_passes_resource_name_and_reconciles_local_state():
    google_result = {
        "display_name": "Updated",
        "resource_name": "people/c1",
        "phones": ["+994559041494"],
    }
    with (
        patch("actions.contacts.update_google_contact", return_value=google_result) as mock_update,
        patch("actions.contacts._reconcile_local_update") as reconcile,
    ):
        result = update_contact("people/c1", "Updated", "+994559041494")

    mock_update.assert_called_once_with("people/c1", "Updated", ["+994559041494"])
    reconcile.assert_called_once_with(google_result)
    assert "yeniləndi" in result
    assert "local phone book" in result


def test_delete_contact_reconciles_local_state_after_verified_google_delete():
    google_result = {
        "resource_name": "people/c1",
        "verification_status": 404,
        "deleted": True,
    }
    with (
        patch("actions.contacts.delete_google_contact", return_value=google_result) as mock_delete,
        patch("actions.contacts._reconcile_local_delete", return_value=True) as reconcile,
    ):
        result = delete_contact("people/c1")

    mock_delete.assert_called_once_with("people/c1")
    reconcile.assert_called_once_with("people/c1")
    assert "HTTP 404" in result
    assert "local phone book-dan da silindi" in result


def test_create_contact_reports_partial_success_when_local_reconciliation_fails():
    google_result = {
        "display_name": "Test",
        "resource_name": "people/c1",
        "phones": ["+994501234567"],
    }
    with (
        patch("actions.contacts.create_google_contact", return_value=google_result),
        patch("actions.contacts._reconcile_local_create", side_effect=OSError("disk failed")),
    ):
        result = create_contact("Test", "0501234567")

    assert "Google kontaktı yaradıldı" in result
    assert "local telefon kitabçası yenilənmədi" in result
