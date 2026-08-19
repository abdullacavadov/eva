from unittest.mock import MagicMock, patch

import pytest

from integrations.google import contacts


def _service():
    return MagicMock()


def test_create_google_contact_uses_people_create_contact():
    service = _service()
    service.people().createContact.return_value.execute.return_value = {
        "resourceName": "people/c123",
        "names": [{"displayName": "Test One"}],
        "phoneNumbers": [{"value": "+994501234567"}],
    }

    with patch.object(contacts, "_get_people_service", return_value=service):
        result = contacts.create_google_contact("Test One", ["+994501234567"])

    assert result == {
        "resource_name": "people/c123",
        "display_name": "Test One",
        "phones": ["+994501234567"],
    }
    service.people().createContact.assert_called_once_with(
        body={
            "names": [{"unstructuredName": "Test One"}],
            "phoneNumbers": [{"value": "+994501234567"}],
        },
        personFields="names,phoneNumbers",
    )


def test_update_google_contact_requires_resource_name():
    with pytest.raises(ValueError, match="resource_name"):
        contacts.update_google_contact("", "Test One", ["+994501234567"])


def test_update_google_contact_reads_current_person_etag_before_update():
    service = _service()
    service.people().get.return_value.execute.return_value = {
        "resourceName": "people/c123",
        "etag": "current-person-etag",
        "metadata": {
            "sources": [
                {"type": "PROFILE", "etag": "profile-etag"},
                {"type": "CONTACT", "etag": "stale-source-etag"},
            ]
        },
    }
    service.people().updateContact.return_value.execute.return_value = {
        "resourceName": "people/c123",
        "names": [{"displayName": "Updated"}],
        "phoneNumbers": [{"value": "+994559041494"}],
    }

    with patch.object(contacts, "_get_people_service", return_value=service):
        result = contacts.update_google_contact(
            "people/c123", "Updated", ["+994559041494"]
        )

    assert result["resource_name"] == "people/c123"
    service.people().get.assert_called_once_with(
        resourceName="people/c123",
        personFields="metadata,names,phoneNumbers",
    )
    service.people().updateContact.assert_called_once_with(
        resourceName="people/c123",
        updatePersonFields="names,phoneNumbers",
        body={
            "resourceName": "people/c123",
            "etag": "current-person-etag",
            "names": [{"unstructuredName": "Updated"}],
            "phoneNumbers": [{"value": "+994559041494"}],
        },
    )


def test_update_google_contact_requires_current_person_etag():
    service = _service()
    service.people().get.return_value.execute.return_value = {
        "resourceName": "people/c123",
        "metadata": {"sources": [{"type": "CONTACT", "etag": "source-etag"}]},
    }

    with patch.object(contacts, "_get_people_service", return_value=service):
        with pytest.raises(ValueError, match="etag"):
            contacts.update_google_contact(
                "people/c123", "Updated", ["+994559041494"]
            )

    service.people().updateContact.assert_not_called()


def test_delete_google_contact_uses_resource_name_only():
    service = _service()

    with patch.object(contacts, "_get_people_service", return_value=service):
        contacts.delete_google_contact("people/c123")

    service.people().deleteContact.assert_called_once_with(resourceName="people/c123")


def test_delete_google_contact_requires_resource_name():
    with pytest.raises(ValueError, match="resource_name"):
        contacts.delete_google_contact("")
