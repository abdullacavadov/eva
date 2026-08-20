import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from actions.email import delete_email, prepare_email_deletion
from integrations.google.gmail import (
    batch_delete_messages,
    delete_draft,
    delete_drafts,
    list_draft_ids,
    list_message_ids,
)


def test_list_draft_ids_paginates():
    service = MagicMock()
    call = service.users.return_value.drafts.return_value.list.return_value
    call.execute.side_effect = [
        {"drafts": [{"id": "d1"}], "nextPageToken": "p2"},
        {"drafts": [{"id": "d2"}]},
    ]

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = list_draft_ids()

    assert result == ["d1", "d2"]
    assert call.execute.call_count == 2


def test_list_message_ids_uses_query_and_spam_trash_flag():
    service = MagicMock()
    method = service.users.return_value.messages.return_value.list
    call = method.return_value
    call.execute.return_value = {"messages": [{"id": "m1"}]}

    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        result = list_message_ids("in:spam", include_spam_trash=True)

    assert result == ["m1"]
    assert method.call_args.kwargs["q"] == "in:spam"
    assert method.call_args.kwargs["includeSpamTrash"] is True


def test_delete_draft_calls_permanent_draft_delete():
    service = MagicMock()
    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        delete_draft("d1")
    service.users.return_value.drafts.return_value.delete.assert_called_once_with(
        userId="me", id="d1"
    )


def test_delete_drafts_deletes_all_targets():
    with patch("integrations.google.gmail.delete_draft") as delete:
        assert delete_drafts(["d1", "d2"]) == 2
    assert [call.args[0] for call in delete.call_args_list] == ["d1", "d2"]


def test_batch_delete_messages_uses_1000_id_chunks():
    service = MagicMock()
    ids = [f"m{i}" for i in range(1001)]
    with patch("integrations.google.gmail.get_gmail_service", return_value=service):
        assert batch_delete_messages(ids) == 1001

    calls = service.users.return_value.messages.return_value.batchDelete.call_args_list
    assert len(calls) == 2
    assert len(calls[0].kwargs["body"]["ids"]) == 1000
    assert len(calls[1].kwargs["body"]["ids"]) == 1


def test_prepare_all_drafts_creates_confirmation_plan():
    with patch("actions.email.list_draft_ids", return_value=["d1", "d2"]):
        result = prepare_email_deletion("drafts")

    assert result["type"] == "email"
    assert result["status"] == "success"
    assert result["data"][0]["scope"] == "drafts"
    assert result["data"][0]["target_count"] == 2
    assert result["data"][0]["permanent"] is True
    assert result["meta"]["requires_confirmation"] is True
    assert result["meta"]["confirmation_action"] == "delete_email"
    assert result["meta"]["confirmation_id"]


def test_prepare_specific_draft_requires_existing_draft():
    with patch("actions.email.get_draft", return_value={"id": "d1"}) as get_draft:
        result = prepare_email_deletion("draft", "d1")

    get_draft.assert_called_once_with("d1")
    assert result["data"][0]["target_count"] == 1


def test_prepare_spam_uses_spam_query():
    with patch("actions.email.list_message_ids", return_value=["m1", "m2"]) as list_messages:
        result = prepare_email_deletion("spam")

    list_messages.assert_called_once_with("in:spam", include_spam_trash=True)
    assert result["data"][0]["target_count"] == 2


def test_prepare_trash_uses_trash_query():
    with patch("actions.email.list_message_ids", return_value=["m1"]) as list_messages:
        result = prepare_email_deletion("trash")

    list_messages.assert_called_once_with("in:trash", include_spam_trash=True)
    assert result["data"][0]["target_count"] == 1


def test_prepare_promotions_and_social_use_categories():
    with patch("actions.email.list_message_ids", side_effect=[["p1"], ["s1", "s2"]]) as list_messages:
        promotions = prepare_email_deletion("promotions")
        social = prepare_email_deletion("social")

    assert promotions["data"][0]["target_count"] == 1
    assert social["data"][0]["target_count"] == 2
    assert list_messages.call_args_list[0].args[0] == "category:promotions"
    assert list_messages.call_args_list[1].args[0] == "category:social"


def test_delete_email_requires_valid_confirmation_and_is_single_use():
    with patch("actions.email.list_draft_ids", return_value=["d1"]), \
         patch("actions.email.delete_drafts", return_value=1) as delete_drafts_mock:
        prepared = prepare_email_deletion("drafts")
        confirmation_id = prepared["meta"]["confirmation_id"]
        result = delete_email(confirmation_id)

    delete_drafts_mock.assert_called_once_with(["d1"])
    assert result["data"][0]["deleted_count"] == 1
    assert result["meta"]["requires_confirmation"] is False

    with pytest.raises(ValueError, match="təsdiqi tapılmadı"):
        delete_email(confirmation_id)


def test_delete_email_rejects_unknown_confirmation():
    with pytest.raises(ValueError, match="confirmation_id"):
        delete_email("")
    with pytest.raises(ValueError, match="təsdiqi tapılmadı"):
        delete_email("unknown")
