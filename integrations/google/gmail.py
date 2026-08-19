from __future__ import annotations

import base64
import html
import re
from typing import Any

from googleapiclient.discovery import build

from integrations.google.auth import get_google_credentials


def get_gmail_service():
    return build("gmail", "v1", credentials=get_google_credentials())


def _decode_body(data: str) -> str:
    raw = base64.urlsafe_b64decode(data.encode("ascii"))
    return raw.decode("utf-8", errors="replace")


def _strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def _headers(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("name", "")).lower(): str(item.get("value", ""))
        for item in payload.get("headers", [])
    }


def _extract_body(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = (payload.get("body") or {}).get("data")
    if body_data:
        text = _decode_body(body_data)
        return _strip_html(text) if "html" in mime_type else text.strip()

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""


def _parse_message(message: dict[str, Any], include_body: bool = False) -> dict[str, str]:
    payload = message.get("payload") or {}
    headers = _headers(payload)
    result = {
        "id": str(message.get("id", "")),
        "thread_id": str(message.get("threadId", "")),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": str(message.get("snippet", "")),
    }
    if include_body:
        result["body"] = _extract_body(payload)
    return result


def search_messages(query: str = "", limit: int = 10) -> list[dict[str, str]]:
    limit = max(1, min(int(limit or 10), 100))
    service = get_gmail_service()
    results: list[dict[str, str]] = []
    page_token = None

    while len(results) < limit:
        kwargs = {
            "userId": "me",
            "q": str(query or "").strip(),
            "maxResults": min(100, limit - len(results)),
        }
        if page_token:
            kwargs["pageToken"] = page_token
        response = service.users().messages().list(**kwargs).execute()
        for item in response.get("messages", []) or []:
            message = service.users().messages().get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            results.append(_parse_message(message))
            if len(results) >= limit:
                break
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def get_message(message_id: str) -> dict[str, str]:
    message_id = str(message_id or "").strip()
    if not message_id:
        raise ValueError("Email message_id tələb olunur.")

    service = get_gmail_service()
    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()
    return _parse_message(message, include_body=True)
