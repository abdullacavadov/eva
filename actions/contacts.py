from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from integrations.google.contacts import (
    create_google_contact,
    delete_google_contact,
    get_google_contacts,
    update_google_contact,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PHONEBOOK_FILE = BASE_DIR / "memory" / "phone_book.json"


def _normalize_lookup(text: str) -> str:
    text = (text or "").strip().casefold()
    text = text.translate(str.maketrans({"ə": "e", "ı": "i", "ö": "o", "ü": "u", "ş": "s", "ç": "c", "ğ": "g"}))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text)


def _normalize_phone(phone_number: str) -> str:
    digits = re.sub(r"\D+", "", phone_number or "")
    if digits.startswith("994"):
        pass
    elif digits.startswith("0") and len(digits) in (10, 11):
        digits = "994" + digits[1:]
    elif len(digits) == 9:
        digits = "994" + digits
    else:
        raise ValueError("Telefon nömrəsi etibarlı beynəlxalq formatda deyil.")
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError("Telefon nömrəsi etibarlı beynəlxalq formatda deyil.")
    return digits


def _contact_key(name: str, phone: str, existing: dict) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", _normalize_lookup(name)).strip("_") or "contact"
    if base not in existing:
        return base
    candidate = f"{base}_{_normalize_phone(phone)[-6:]}"
    if candidate not in existing:
        return candidate
    index = 2
    while f"{candidate}_{index}" in existing:
        index += 1
    return f"{candidate}_{index}"


def _entry_phones(entry: dict) -> list[str]:
    values = []
    for key in ("value", "phone_number", "phone", "number", "mobile", "tel"):
        value = entry.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            values.append(str(value).strip())
    for key in ("phones", "numbers", "phone_numbers"):
        value = entry.get(key)
        if isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, (str, int)):
                    values.append(str(item).strip())
                elif isinstance(item, dict):
                    nested = item.get("value") or item.get("number") or item.get("phone")
                    if nested:
                        values.append(str(nested).strip())
    normalized = []
    for value in values:
        try:
            normalized.append(_normalize_phone(value))
        except ValueError:
            continue
    return list(dict.fromkeys(normalized))


def _build_entry(contact: dict, phones: list[str], previous: dict | None = None) -> dict:
    display_name = contact["display_name"]
    entry = dict(previous or {})
    entry["display_name"] = display_name
    previous_phones = set(_entry_phones(previous or {}))
    if previous is None or previous_phones != set(phones):
        entry["value"] = f"+{phones[0]}"
        entry["phones"] = [{"number": f"+{phone}"} for phone in phones]
    resource_name = contact.get("resource_name")
    if resource_name and (previous is None or "google_resource_name" in previous):
        entry["google_resource_name"] = resource_name
    return entry


def _find_match(local: dict, contact: dict, phones: list[str]) -> tuple[str | None, dict | None]:
    resource_name = contact.get("resource_name")
    if resource_name:
        for key, entry in local.items():
            if isinstance(entry, dict) and entry.get("google_resource_name") == resource_name:
                return key, entry
    phone_set = set(phones)
    if phone_set:
        for key, entry in local.items():
            if isinstance(entry, dict) and phone_set.intersection(_entry_phones(entry)):
                return key, entry
    normalized_name = _normalize_lookup(contact["display_name"])
    if normalized_name:
        for key, entry in local.items():
            if isinstance(entry, dict) and _normalize_lookup(str(entry.get("display_name") or key)) == normalized_name:
                return key, entry
    return None, None


def _write_atomic(phone_book: dict) -> None:
    PHONEBOOK_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="phone_book_", suffix=".json", dir=str(PHONEBOOK_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(phone_book, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_path, PHONEBOOK_FILE)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def sync_google_contacts() -> str:
    """Synchronize Google Contacts into the local phone book without deleting local-only entries."""
    try:
        local = json.loads(PHONEBOOK_FILE.read_text(encoding="utf-8")) if PHONEBOOK_FILE.exists() else {}
    except (json.JSONDecodeError, OSError) as exc:
        return f"Local telefon kitabçası oxunmadı: {exc}"
    if not isinstance(local, dict):
        return "Local telefon kitabçasının strukturu düzgün deyil."
    try:
        google_contacts = get_google_contacts()
    except Exception as exc:
        return f"Google Contacts sinxronizasiyası alınmadı: {exc}"

    merged = dict(local)
    added = updated = unchanged = 0
    seen_google_phones: set[str] = set()
    seen_google_resources: set[str] = set()
    try:
        for contact in google_contacts:
            display_name = str(contact.get("display_name") or "").strip()
            phones = []
            for raw_phone in contact.get("phones") or []:
                try:
                    normalized = _normalize_phone(str(raw_phone))
                except ValueError:
                    continue
                if normalized not in phones:
                    phones.append(normalized)
            if not display_name or not phones:
                continue
            resource_name = str(contact.get("resource_name") or "")
            if resource_name and resource_name in seen_google_resources:
                continue
            if resource_name:
                seen_google_resources.add(resource_name)
            phone_set = set(phones)
            if phone_set.intersection(seen_google_phones):
                continue
            seen_google_phones.update(phone_set)
            normalized_contact = {"display_name": display_name, "resource_name": resource_name}
            key, previous = _find_match(merged, normalized_contact, phones)
            if key is None:
                key = _contact_key(display_name, phones[0], merged)
                merged[key] = _build_entry(normalized_contact, phones)
                added += 1
                continue
            desired = _build_entry(normalized_contact, phones, previous)
            if desired == previous:
                unchanged += 1
            else:
                merged[key] = desired
                updated += 1
        if merged != local:
            _write_atomic(merged)
    except Exception as exc:
        return f"Kontakt sinxronizasiyası zamanı local telefon kitabçası dəyişdirilmədi: {exc}"
    return f"Google Contacts sinxronizasiya edildi: {added} yeni, {updated} yenilənmiş, {unchanged} dəyişməyən kontakt. Local-only kontaktlar saxlanıldı."


def create_contact(display_name: str, phone_number: str) -> str:
    """Create a Google Contact without modifying the local phone book."""
    phone = _normalize_phone(phone_number)
    contact = create_google_contact(display_name, [f"+{phone}"])
    return f"Google kontaktı yaradıldı: {contact['display_name']} ({contact['resource_name']})."


def update_contact(resource_name: str, display_name: str, phone_number: str) -> str:
    """Update a Google Contact using its known resource identity."""
    phone = _normalize_phone(phone_number)
    contact = update_google_contact(resource_name, display_name, [f"+{phone}"])
    return f"Google kontaktı yeniləndi: {contact['display_name']} ({contact['resource_name']})."


def delete_contact(resource_name: str) -> str:
    """Delete a Google Contact using its known resource identity."""
    result = delete_google_contact(resource_name)
    return (
        f"Google kontaktı silindi və GET verification ilə HTTP "
        f"{result['verification_status']} təsdiqləndi: {result['resource_name']}."
    )
