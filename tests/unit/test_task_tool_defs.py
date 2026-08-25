from core.task_tool_defs import TASK_TOOL_DECLARATIONS


def test_unified_query_tool_is_declared():
    names = {item["name"] for item in TASK_TOOL_DECLARATIONS}
    assert "query_unified_assistant" in names


def test_retired_microsoft_todo_is_not_declared():
    text = str(TASK_TOOL_DECLARATIONS).casefold()
    assert "microsoft todo" not in text
    assert "microsoft_todo" not in text
