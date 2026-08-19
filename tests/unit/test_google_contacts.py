from unittest.mock import MagicMock, patch

from integrations.google import contacts


def test_get_google_contacts_reads_all_pages():
    service = MagicMock()
    service.people().connections().list().execute.side_effect = [
        {
            "connections": [
                {
                    "resourceName": "people/1",
                    "names": [{"displayName": "Test One"}],
                    "phoneNumbers": [{"value": "+994501234567"}],
                }
            ],
            "nextPageToken": "next",
        },
        {
            "connections": [
                {
                    "resourceName": "people/2",
                    "names": [{"displayName": "Test Two"}],
                    "phoneNumbers": [{"value": "+994559041494"}],
                }
            ]
        },
    ]

    with patch.object(contacts, "get_google_credentials", return_value=MagicMock()), patch(
        "integrations.google.contacts.build", return_value=service
    ):
        result = contacts.get_google_contacts()

    assert result == [
        {
            "resource_name": "people/1",
            "display_name": "Test One",
            "phones": ["+994501234567"],
        },
        {
            "resource_name": "people/2",
            "display_name": "Test Two",
            "phones": ["+994559041494"],
        },
    ]
    assert service.people().connections().list.call_count == 2
