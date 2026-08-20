from core.email_tool_defs import EMAIL_TOOL_DECLARATIONS


def _tool(name):
    return next(item for item in EMAIL_TOOL_DECLARATIONS if item["name"] == name)


def test_prepare_email_deletion_declares_all_scopes():
    tool = _tool("prepare_email_deletion")
    scope = tool["parameters"]["properties"]["scope"]
    assert scope["enum"] == ["drafts", "draft", "spam", "trash", "promotions", "social"]
    assert "draft_id" in tool["parameters"]["properties"]


def test_delete_email_requires_confirmation_id():
    tool = _tool("delete_email")
    assert tool["parameters"]["required"] == ["confirmation_id"]
    assert "təsdiq" in tool["description"]
