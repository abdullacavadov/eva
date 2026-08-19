from unittest.mock import MagicMock, patch

from integrations.google.auth import SCOPES, get_google_credentials


def test_google_scopes_include_calendar_and_tasks():
    assert "https://www.googleapis.com/auth/calendar" in SCOPES
    assert "https://www.googleapis.com/auth/tasks" in SCOPES


@patch("integrations.google.auth.TOKEN_FILE")
def test_existing_valid_token_is_reused(mock_token_file):
    mock_token_file.exists.return_value = True
    credentials = MagicMock()
    credentials.expired = False
    credentials.valid = True

    with patch(
        "integrations.google.auth.Credentials.from_authorized_user_file",
        return_value=credentials,
    ) as mock_from_file:
        result = get_google_credentials()

    mock_from_file.assert_called_once_with(str(mock_token_file), SCOPES)
    mock_token_file.write_text.assert_called_once_with(
        credentials.to_json(), encoding="utf-8"
    )
    assert result is credentials


@patch("integrations.google.auth.TOKEN_FILE")
def test_expired_token_refreshes(mock_token_file):
    mock_token_file.exists.return_value = True
    credentials = MagicMock()
    credentials.expired = True
    credentials.refresh_token = "refresh-token"
    credentials.valid = True

    with patch(
        "integrations.google.auth.Credentials.from_authorized_user_file",
        return_value=credentials,
    ), patch("integrations.google.auth.Request"):
        result = get_google_credentials()

    credentials.refresh.assert_called_once()
    assert result is credentials
