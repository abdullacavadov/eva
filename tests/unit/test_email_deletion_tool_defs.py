from core.email_tool_defs import EMAIL_TOOL_DECLARATIONS


def test_permanent_email_delete_tools_are_not_exposed():
    names = {item["name"] for item in EMAIL_TOOL_DECLARATIONS}
    assert "prepare_email_deletion" not in names
    assert "delete_email" not in names
