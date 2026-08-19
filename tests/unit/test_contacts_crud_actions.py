from unittest.mock import patch

import pytest

from actions.contacts import create_contact, delete_contact, update_contact


def test_create_contact_normalizes_phone_before_google_write():
    with patch("actions.contacts.create_google_contact", return_value={"display_name": "Test", "resource_name": "people/c1"}) as mock_create:
        result = create_contact("Test", "0501234567")

    mock_create.assert_called_once_with("Test", ["+994501234567"])
    assert "people/c1" in result


def test_update_contact_requires_valid_phone():
    with pytest.raises(ValueError, match="Telefon nömrəsi"):
        update_contact("people/c1", "Test", "123")


def test_update_contact_passes_resource_name():
    with patch("actions.contacts.update_google_contact", return_value={"display_name": "Updated", "resource_name": "people/c1"}) as mock_update:
        result = update_contact("people/c1", "Updated", "+994559041494")

    mock_update.assert_called_once_with("people/c1", "Updated", ["+994559041494"])
    assert "yeniləndi" in result


def test_delete_contact_passes_resource_name():
    with patch("actions.contacts.delete_google_contact") as mock_delete:
        result = delete_contact("people/c1")

    mock_delete.assert_called_once_with("people/c1")
    assert "silindi" in result
