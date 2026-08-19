from __future__ import annotations

from googleapiclient.discovery import build

from integrations.google.auth import get_google_credentials


def get_google_contacts() -> list[dict]:
    """Return Google Contacts as normalized name/phone/resource records."""
    credentials = get_google_credentials()
    service = build("people", "v1", credentials=credentials, cache_discovery=False)

    contacts: list[dict] = []
    page_token = None

    while True:
        response = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                pageSize=100,
                pageToken=page_token,
                personFields="names,phoneNumbers",
            )
            .execute()
        )

        for person in response.get("connections", []):
            names = person.get("names") or []
            display_name = ""
            if names:
                display_name = str(
                    names[0].get("displayName")
                    or names[0].get("unstructuredName")
                    or ""
                ).strip()

            phones = []
            for phone in person.get("phoneNumbers") or []:
                number = str(phone.get("value") or "").strip()
                if number:
                    phones.append(number)

            if not display_name or not phones:
                continue

            contacts.append(
                {
                    "resource_name": str(person.get("resourceName") or ""),
                    "display_name": display_name,
                    "phones": phones,
                }
            )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return contacts
