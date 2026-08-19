import pytest

from core.result_context import ResultContext
from core.result_resolver import ResultResolutionError, resolve_item
from core.result_store import ResultStore


def _context(items):
    return ResultContext.from_result(
        "r1",
        {
            "type": "calendar_event",
            "status": "success",
            "query": {},
            "data": items,
            "count": len(items),
        },
        1800,
    )


def test_resolve_item_by_exact_title():
    item = resolve_item(
        _context([
            {"id": "calendar_event:e1", "summary": "Dentist"},
            {"id": "calendar_event:e2", "summary": "Meeting"},
        ]),
        "Dentist",
    )
    assert item["id"] == "calendar_event:e1"


def test_resolve_item_by_partial_match():
    item = resolve_item(_context([{ "id": "email:m1", "subject": "Dentist appointment" }]), "Dentist")
    assert item["id"] == "email:m1"


def test_resolve_item_is_case_insensitive():
    item = resolve_item(_context([{ "id": "contact:c1", "display_name": "Əhməd" }]), "əhməd")
    assert item["id"] == "contact:c1"


def test_resolve_item_rejects_ambiguous_match():
    with pytest.raises(ResultResolutionError, match="Bir neçə"):
        resolve_item(
            _context([
                {"id": "calendar_event:e1", "summary": "Dentist morning"},
                {"id": "calendar_event:e2", "summary": "Dentist evening"},
            ]),
            "Dentist",
        )


def test_resolve_item_rejects_missing_match():
    with pytest.raises(ResultResolutionError, match="tapılmadı"):
        resolve_item(_context([{ "id": "calendar_event:e1", "summary": "Meeting" }]), "Dentist")


def test_resolve_item_rejects_empty_result():
    with pytest.raises(ResultResolutionError, match="boşdur"):
        resolve_item(_context([]), "Dentist")


def test_store_select_and_get_selected():
    store = ResultStore()
    result_id = store.save({
        "type": "calendar_event",
        "status": "success",
        "query": {},
        "data": [
            {"id": "calendar_event:e1", "summary": "Dentist"},
            {"id": "calendar_event:e2", "summary": "Meeting"},
        ],
    })
    selected = store.select(result_id, "calendar_event:e1")
    assert selected["summary"] == "Dentist"
    assert store.selected()["id"] == "calendar_event:e1"


def test_store_select_rejects_unknown_item():
    store = ResultStore()
    result_id = store.save({"type": "contact", "status": "success", "query": {}, "data": [{"id": "contact:c1", "display_name": "Abu"}]})
    with pytest.raises(KeyError):
        store.select(result_id, "contact:missing")
