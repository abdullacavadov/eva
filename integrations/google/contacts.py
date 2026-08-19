from __future__ import annotations

from googleapiclient.discovery import build

from integrations.google.auth import get_google_credentials


PERSON_FIELDS = "names,phoneNumbers"
UPDATE_PERSON_FIELDS = PERSON_FIELDS
UPDATE_PERSON_GET_FIELDS = "metadata,names,phoneNumbers"


def _build_person(display_name: str, phones: list[str]) -> dict:
    person = {"names": [{"unstructuredName": display_name}]}
    if phones:
        person["phoneNumbers"] = [{"value": phone} for phone in phones]
    return person


def _get_people_service():
    credentials = get_google_credentials()
    return build("people", "v1", credentials=credentials, cache_discovery=False)


def get_google_contacts() -> list[dict]:
    """Return Google Contacts as normalized name/phone/resource records."""
    service = _get_people_service()
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
                personFields=PERSON_FIELDS,
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


def create_google_contact(display_name: str, phones: list[str]) -> dict:
    """Create a Google Contact and return its resource identity and fields."""
    if not display_name.strip():
        raise ValueError("Kontakt adı tələb olunur.")
    if not phones:
        raise ValueError("Ən azı bir telefon nömrəsi tələb olunur.")

    service = _get_people_service()
    response = (
        service.people()
        .createContact(
            body=_build_person(display_name.strip(), phones),
            personFields=PERSON_FIELDS,
        )
        .execute()
    )
    return {
        "resource_name": str(response.get("resourceName") or ""),
        "display_name": str((response.get("names") or [{}])[0].get("displayName") or display_name).strip(),
        "phones": [
            str(phone.get("value") or "").strip()
            for phone in response.get("phoneNumbers") or []
            if str(phone.get("value") or "").strip()
        ],
    }


def _get_contact_etag(service, resource_name: str) -> str:
    """Read the current person etag required by Google updateContact."""
    response = (
        service.people()
        .get(resourceName=resource_name, personFields=UPDATE_PERSON_GET_FIELDS)
        .execute()
    )
    etag = str(response.get("etag") or "").strip()
    if not etag:
        raise ValueError("Google kontaktının aktual etag məlumatı tapılmadı.")
    return etag


def update_google_contact(resource_name: str, display_name: str, phones: list[str]) -> dict:
    """Update a Google Contact by resource name using its current person etag."""
    if not resource_name.strip():
        raise ValueError("Google contact resource_name tələb olunur.")
    if not display_name.strip():
        raise ValueError("Kontakt adı tələb olunur.")
    if not phones:
        raise ValueError("Ən azı bir telefon nömrəsi tələb olunur.")

    resource_name = resource_name.strip()
    service = _get_people_service()
    etag = _get_contact_etag(service, resource_name)
    response = (
        service.people()
        .updateContact(
            resourceName=resource_name,
            updatePersonFields=UPDATE_PERSON_FIELDS,
            body={
                "resourceName": resource_name,
                "etag": etag,
                **_build_person(display_name.strip(), phones),
            },
        )
        .execute()
    )
    return {
        "resource_name": str(response.get("resourceName") or resource_name).strip(),
        "display_name": str((response.get("names") or [{}])[0].get("displayName") or display_name).strip(),
        "phones": [
            str(phone.get("value") or "").strip()
            for phone in response.get("phoneNumbers") or []
            if str(phone.get("value") or "").strip()
        ],
    }


def delete_google_contact(resource_name: str) -> None:
    """Delete a Google Contact by its resource name only."""
    if not resource_name.strip():
        raise ValueError("Google contact resource_name tələb olunur.")

    service = _get_people_service()
    service.people().deleteContact(resourceName=resource_name.strip()).execute()
