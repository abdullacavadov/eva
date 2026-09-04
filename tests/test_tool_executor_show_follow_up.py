from core.tool_executor import _is_implicit_show_query


def test_named_show_query_is_recognized():
    assert _is_implicit_show_query("Həmin partini göstər baxım") is True
    assert _is_implicit_show_query("Ev partisini göstər") is True


def test_unrelated_query_is_not_recognized_as_show():
    assert _is_implicit_show_query("parti haqqında məlumat ver") is False
