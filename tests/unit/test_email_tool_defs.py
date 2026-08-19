from tool_defs import TOOL_DECLARATIONS


def test_gmail_read_tools_are_registered():
    names = {item["name"] for item in TOOL_DECLARATIONS}
    assert "get_emails" in names
    assert "read_email" in names


def test_gmail_read_tools_are_read_only():
    by_name = {item["name"]: item for item in TOOL_DECLARATIONS}
    assert "send" not in by_name["get_emails"]["name"]
    assert "modify" not in by_name["get_emails"]["name"]
