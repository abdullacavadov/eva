from __future__ import annotations

import base64
import html
import re

from typing import Any
from email.message import EmailMessage
from googleapiclient.discovery import build
from integrations.google.auth import get_google_credentials


GMAIL_FOLDER_QUERIES = {
    "inbox": "in:inbox",
    "sent": "in:sent",
    "drafts": "in:drafts",
    "spam": "category:spam",
    "trash": "in:trash",
    "promotions": "category:promotions",
    "social": "category:social",
    "updates": "category:updates",
    "purchases": "category:purchases",
    "starred": "is:starred",
    "all_mail": "-in:spam -in:trash",
}


def get_gmail_service():
    return build("gmail", "v1", credentials=get_google_credentials())


def _decode_body(data: str) -> str:
    raw = base64.urlsafe_b64decode(data.encode("ascii"))
    return raw.decode("utf-8", errors="replace")


def _strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def get_message(message_id: str) -> dict[str, str]:
    message_id = str(message_id or "").strip()
    if not message_id:
        raise ValueError("Email message_id tələb olunur.")

    service = get_gmail_service()

    response = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()

    return _parse_message(response, include_body=True)


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


def list_draft_ids() -> list[str]:
    service = get_gmail_service()
    draft_ids: list[str] = []
    page_token = None

    while True:
        kwargs = {
            "userId": "me",
            "maxResults": 100,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().drafts().list(**kwargs).execute()
        draft_ids.extend(
            str(item["id"])
            for item in response.get("drafts", []) or []
            if item.get("id")
        )
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return draft_ids


def get_draft(draft_id: str) -> dict[str, Any]:
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        raise ValueError("Email draft_id tələb olunur.")

    service = get_gmail_service()
    return service.users().drafts().get(
        userId="me",
        id=draft_id,
        format="metadata",
    ).execute()


def list_message_ids(query: str, include_spam_trash: bool = False) -> list[str]:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Gmail delete query tələb olunur.")

    service = get_gmail_service()
    message_ids: list[str] = []
    page_token = None
    include_scoped_spam_trash = bool(
        include_spam_trash or "in:spam" in query or "in:trash" in query
    )

    while True:
        kwargs = {
            "userId": "me",
            "q": query,
            "maxResults": 100,
            "includeSpamTrash": include_scoped_spam_trash,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        message_ids.extend(
            str(item["id"])
            for item in response.get("messages", []) or []
            if item.get("id")
        )
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return message_ids


def delete_draft(draft_id: str) -> None:
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        raise ValueError("Email draft_id tələb olunur.")

    service = get_gmail_service()
    service.users().drafts().delete(
        userId="me",
        id=draft_id,
    ).execute()


def delete_drafts(draft_ids: list[str]) -> int:
    for draft_id in draft_ids:
        delete_draft(draft_id)
    return len(draft_ids)


def batch_delete_messages(message_ids: list[str]) -> int:
    message_ids = [str(message_id).strip()
                   for message_id in message_ids if str(message_id).strip()]
    if not message_ids:
        return 0

    service = get_gmail_service()
    for start in range(0, len(message_ids), 1000):
        chunk = message_ids[start:start + 1000]
        service.users().messages().batchDelete(
            userId="me",
            body={"ids": chunk},
        ).execute()
    return len(message_ids)


def _parse_message(message: dict[str, Any], include_body: bool = False) -> dict[str, str]:
    payload = message.get("payload") or {}
    headers = _headers(payload)

    result = {
        "id": str(message.get("id", "")),
        "thread_id": str(message.get("threadId", "")),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "bcc": headers.get("bcc", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": str(message.get("snippet", "")),
        "message_id_header": headers.get("message-id", ""),
        "references": headers.get("references", ""),
        "in_reply_to": headers.get("in-reply-to", ""),
    }

    if include_body:
        result["body"] = _extract_body(payload)

    return result


def folder_query(folder: str) -> str:
    folder = str(folder or "").strip().lower()
    if not folder:
        return ""
    try:
        return GMAIL_FOLDER_QUERIES[folder]
    except KeyError as exc:
        raise ValueError(
            "Dəstəklənən Gmail qovluqları: inbox, sent, drafts, spam, trash, promotions, social, updates, purchases, starred, all_mail."
        ) from exc


def search_messages(
    query: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 10), 100))
    service = get_gmail_service()
    results: list[dict[str, str]] = []
    page_token = None
    total_count = 0
    has_more = False

    while len(results) < limit:
        kwargs = {
            "userId": "me",
            "q": str(query or "").strip(),
            "maxResults": min(100, limit - len(results)),
        }
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        total_count = int(
            response.get(
                "resultSizeEstimate",
                total_count,
            )
            or 0
        )

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
            has_more = False
            break

        has_more = len(results) < limit

    if total_count == 0 and results:
        total_count = len(results)

    return {
        "messages": results,
        "count": total_count,
        "returned_count": len(results),
        "has_more": has_more,
    }


def trash_message(message_id: str) -> dict[str, str]:
    message_id = str(message_id or "").strip()
    if not message_id:
        raise ValueError("Email message_id tələb olunur.")

    service = get_gmail_service()
    response = service.users().messages().trash(
        userId="me",
        id=message_id,
    ).execute()

    return {
        "message_id": str(response.get("id", message_id)),
        "thread_id": str(response.get("threadId", "")),
    }


def trash_messages_by_query(query: str) -> dict[str, int]:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Trash əməliyyatı üçün Gmail query tələb olunur.")

    service = get_gmail_service()
    page_token = None
    matched = 0
    trashed = 0
    include_scoped_spam_trash = "in:spam" in query or "in:trash" in query

    while True:
        kwargs = {
            "userId": "me",
            "q": query,
            "maxResults": 100,
            "includeSpamTrash": include_scoped_spam_trash,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        message_ids = [
            str(item.get("id", ""))
            for item in response.get("messages", []) or []
            if item.get("id")
        ]
        matched += len(message_ids)

        for message_id in message_ids:
            service.users().messages().trash(
                userId="me",
                id=message_id,
            ).execute()
            trashed += 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return {
        "matched_count": matched,
        "trashed_count": trashed,
    }


def get_thread(thread_id: str) -> list[dict[str, str]]:
    thread_id = str(thread_id or "").strip()
    if not thread_id:
        raise ValueError("Email thread_id tələb olunur.")

    service = get_gmail_service()

    response = service.users().threads().get(
        userId="me",
        id=thread_id,
        format="full",
    ).execute()

    return [
        _parse_message(message, include_body=True)
        for message in response.get("messages", []) or []
    ]


def create_draft(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
    thread_id: str = "",
    in_reply_to: str = "",
    references: str = "",
) -> dict[str, str]:
    to = str(to or "").strip()
    subject = str(subject or "").strip()
    body = str(body or "")

    if not to:
        raise ValueError("Email recipient tələb olunur.")
    if not subject:
        raise ValueError("Email subject tələb olunur.")
    if not body.strip():
        raise ValueError("Email body boş ola bilməz.")

    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject

    if cc.strip():
        message["Cc"] = cc.strip()

    if bcc.strip():
        message["Bcc"] = bcc.strip()

    if in_reply_to.strip():
        message["In-Reply-To"] = in_reply_to.strip()

    if references.strip():
        message["References"] = references.strip()

    message.set_content(body)

    raw = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("ascii")

    gmail_message = {
        "raw": raw,
    }

    if thread_id.strip():
        gmail_message["threadId"] = thread_id.strip()

    service = get_gmail_service()

    response = service.users().drafts().create(
        userId="me",
        body={
            "message": gmail_message,
        },
    ).execute()

    draft_id = str(response.get("id", ""))
    message_data = response.get("message") or {}

    if not draft_id:
        raise RuntimeError("Gmail draft ID qaytarmadı.")

    return {
        "draft_id": draft_id,
        "gmail_message_id": str(message_data.get("id", "")),
        "thread_id": str(message_data.get("threadId", thread_id)),
    }


def send_draft(draft_id: str) -> dict[str, str]:
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        raise ValueError("Email draft_id tələb olunur.")

    service = get_gmail_service()

    response = service.users().drafts().send(
        userId="me",
        body={
            "id": draft_id,
        },
    ).execute()

    return {
        "message_id": str(response.get("id", "")),
        "thread_id": str(response.get("threadId", "")),
    }
