from tool_defs import TOOL_DECLARATIONS


def test_gmail_read_tools_are_registered():
    names = {item["name"] for item in TOOL_DECLARATIONS}
    assert "get_emails" in names
    assert "read_email" in names


def test_gmail_communication_tools_are_registered():
    names = {item["name"] for item in TOOL_DECLARATIONS}
    assert "read_email_thread" in names
    assert "prepare_email_reply" in names
    assert "prepare_new_email" in names
    assert "send_email" in names
    assert "prepare_email_deletion" in names
    assert "delete_email" in names


def test_gmail_read_tools_are_read_only():
    by_name = {item["name"]: item for item in TOOL_DECLARATIONS}
    assert "send" not in by_name["get_emails"]["name"]
    assert "modify" not in by_name["get_emails"]["name"]


def test_send_email_requires_draft_id():
    by_name = {item["name"]: item for item in TOOL_DECLARATIONS}
    send = by_name["send_email"]
    assert send["parameters"]["required"] == ["draft_id"]


def test_draft_tools_require_confirmation_in_description():
    by_name = {item["name"]: item for item in TOOL_DECLARATIONS}
    assert "təsdiq" in by_name["prepare_email_reply"]["description"].lower()
    assert "təsdiq" in by_name["prepare_new_email"]["description"].lower()
    assert "təsdiq" in by_name["send_email"]["description"].lower()


def test_permanent_email_delete_tools_have_confirmation_boundary():
    by_name = {item["name"]: item for item in TOOL_DECLARATIONS}

    prepare = by_name["prepare_email_deletion"]
    delete = by_name["delete_email"]

    assert prepare["parameters"]["required"] == ["scope"]
    assert delete["parameters"]["required"] == ["confirmation_id"]

    description = prepare["description"].lower()
    assert "təsdiq" in description
    assert "həmişəlik" in description
    assert "drafts" in description
    assert "draft" in description
    assert "spam" in description
    assert "trash" in description
    assert "promotions" in description
    assert "social" in description

    delete_description = delete["description"].lower()
    assert "təsdiq" in delete_description
    assert "confirmation_id" in delete_description