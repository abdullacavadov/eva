from unittest.mock import MagicMock, patch

from integrations.google.auth import SCOPES, get_google_credentials


def test_google_scopes_include_calendar_tasks_and_gmail_readonly():
    assert "https://www.googleapis.com/auth/calendar" in SCOPES
    assert "https://www.googleapis.com/auth/tasks" in SCOPES
    assert "https://www.googleapis.com/auth/gmail.readonly" in SCOPES


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


@patch("integrations.google.auth.TOKEN_FILE")
@patch("integrations.google.auth.CREDENTIALS_FILE")
@patch("integrations.google.auth.InstalledAppFlow")
def test_scope_mismatch_triggers_reauthorization(
    mock_flow_class, mock_credentials_file, mock_token_file
):
    mock_token_file.exists.return_value = True
    mock_credentials_file.exists.return_value = True

    old_credentials = MagicMock()
    old_credentials.expired = False
    old_credentials.valid = True
    old_credentials.has_scopes.return_value = False

    new_credentials = MagicMock()
    new_credentials.expired = False
    new_credentials.valid = True
    new_credentials.has_scopes.return_value = True

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = new_credentials
    mock_flow_class.from_client_secrets_file.return_value = mock_flow

    with patch(
        "integrations.google.auth.Credentials.from_authorized_user_file",
        return_value=old_credentials,
    ):
        result = get_google_credentials()

    mock_flow_class.from_client_secrets_file.assert_called_once_with(
        str(mock_credentials_file), SCOPES
    )
    mock_flow.run_local_server.assert_called_once_with(
        port=0,
        access_type="offline",
        prompt="consent",
    )
    assert result is new_credentials
