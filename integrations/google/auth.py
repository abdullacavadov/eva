from __future__ import annotations

import json
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"

CREDENTIALS_FILE = CONFIG_DIR / "google_credentials.json"
TOKEN_FILE = CONFIG_DIR / "google_token.json"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://mail.google.com/",
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
            "Google OAuth üçün tələb olunan Calendar, Tasks, Gmail, Contacts və hesab məlumatı scope-ları çatışmır."
        )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    return credentials


def get_google_account_email(credentials: Credentials | None = None) -> str | None:
    """Qoşulmuş Google hesabının email ünvanını təhlükəsiz şəkildə qaytarır."""
    credentials = credentials or get_google_credentials()
    if not credentials.valid:
        return None

    try:
        response = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=10,
        )
        response.raise_for_status()
        email = response.json().get("email")
        return str(email).strip() if email else None
    except Exception:
        return None


def is_google_connected() -> bool:
    """Lokal Google OAuth tokenının mövcud və istifadə edilə bilən olub-olmadığını yoxlayır."""
    if not TOKEN_FILE.exists():
        return False
    try:
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
        return bool(credentials.valid and _has_required_scopes(credentials))
    except Exception:
        return False


def disconnect_google() -> None:
    """Google OAuth tokenını lokal sistemdən silir."""
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
    except OSError as exc:
        raise RuntimeError(f"Google hesabı ayrıla bilmədi: {exc}") from exc


def get_calendar_credentials() -> Credentials:
    """Backward-compatible alias for existing Calendar callers."""
    return get_google_credentials()
