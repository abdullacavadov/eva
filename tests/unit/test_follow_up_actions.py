import pytest

from core.result_context import ResultContext
from core.result_resolver import ResultResolutionError, resolve_follow_up_action


def _context(items):
    return ResultContext.from_result(
        "r1",
        {
            "type": "task",
            "status": "success",
            "query": {},
            "data": items,
            "count": len(items),
        },
        1800,
    )


def test_follow_up_show_resolves_ordinal_reference():
    result = resolve_follow_up_action(
        _context([
            {"id": "tasks:t1", "title": "Birinci"},
            {"id": "tasks:t2", "title": "İkinci"},
        ]),
        "ikincini göstər",
    )

    assert result.reference == "ikincini"
    assert result.action == "show"
    assert result.item["id"] == "tasks:t2"


def test_follow_up_complete_resolves_ordinal_reference():
    result = resolve_follow_up_action(
        _context([
            {"id": "tasks:t1", "title": "Birinci"},
            {"id": "tasks:t2", "title": "İkinci"},
        ]),
        "ikincini tamamla",
    )

    assert result.reference == "ikincini"
    assert result.action == "complete"
    assert result.item["id"] == "tasks:t2"


def test_follow_up_delete_resolves_selected_pronoun():
    context = _context([
        {"id": "tasks:t1", "title": "Birinci"},
        {"id": "tasks:t2", "title": "İkinci"},
    ])

    result = resolve_follow_up_action(context, "onu sil", selected_item=context.data[1])

    assert result.reference == "onu"
    assert result.action == "delete"
    assert result.item["id"] == "tasks:t2"


def test_follow_up_update_resolves_selected_pronoun():
    context = _context([
        {"id": "tasks:t1", "title": "Birinci"},
        {"id": "tasks:t2", "title": "İkinci"},
    ])

    result = resolve_follow_up_action(context, "bunu sabaha keçir", selected_item=context.data[0])

    assert result.reference == "bunu"
    assert result.action == "update"
    assert result.item["id"] == "tasks:t1"


def test_follow_up_rejects_unknown_action():
    with pytest.raises(ResultResolutionError, match="əməl"):
        resolve_follow_up_action(
            _context([{"id": "tasks:t1", "title": "Task"}]),
            "onu sehrlə",
            selected_item={"id": "tasks:t1", "title": "Task"},
        )


def test_follow_up_rejects_ambiguous_pronoun():
    with pytest.raises(ResultResolutionError, match="konkret nəticə"):
        resolve_follow_up_action(
            _context([
                {"id": "tasks:t1", "title": "Birinci"},
                {"id": "tasks:t2", "title": "İkinci"},
            ]),
            "onu sil",
        )
