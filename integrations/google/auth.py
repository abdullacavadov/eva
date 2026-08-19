from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"

CREDENTIALS_FILE = CONFIG_DIR / "google_credentials.json"
TOKEN_FILE = CONFIG_DIR / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/contacts",
]


def _has_required_scopes(credentials: Credentials) -> bool:
    return all(credentials.has_scopes([scope]) for scope in SCOPES)


def get_google_credentials() -> Credentials:
    credentials = None

    if TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(TOKEN_FILE),
                SCOPES,
            )
            if not _has_required_scopes(credentials):
                credentials = None
        except (json.JSONDecodeError, ValueError, OSError):
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception:
            credentials = None

    if not credentials or not credentials.valid:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"Google credentials tapılmadı: {CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES,
        )

        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
        )

    if not _has_required_scopes(credentials):
        raise RuntimeError(
            "Google OAuth üçün Calendar, Tasks, Gmail readonly və Contacts scope-ları tələb olunur."
        )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    return credentials


def get_calendar_credentials() -> Credentials:
    """Backward-compatible alias for existing Calendar callers."""
    return get_google_credentials()
