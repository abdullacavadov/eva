import pytest

from core.result_context import ResultContext
from core.result_resolver import ResultResolutionError, resolve_item, resolve_reference
from core.result_store import ResultStore


def _context(items):
    return ResultContext.from_result("r1", {"type": "calendar_event", "status": "success", "query": {}, "data": items, "count": len(items)}, 1800)


def test_resolve_item_by_exact_title():
    item = resolve_item(_context([{"id": "calendar_event:e1", "summary": "Dentist"}, {"id": "calendar_event:e2", "summary": "Meeting"}]), "Dentist")
    assert item["id"] == "calendar_event:e1"


def test_resolve_item_by_follow_up_command():
    item = resolve_item(_context([{"id": "calendar_event:e1", "summary": "Dentist"}, {"id": "calendar_event:e2", "summary": "Meeting"}]), "Dentist-i aç")
    assert item["id"] == "calendar_event:e1"


def test_resolve_item_by_partial_match():
    item = resolve_item(_context([{ "id": "email:m1", "subject": "Dentist appointment" }]), "Dentist")
    assert item["id"] == "email:m1"


def test_resolve_item_is_case_insensitive():
    item = resolve_item(_context([{ "id": "contact:c1", "display_name": "Əhməd" }]), "əhməd")
    assert item["id"] == "contact:c1"


def test_resolve_item_rejects_ambiguous_match():
    with pytest.raises(ResultResolutionError, match="Bir neçə"):
        resolve_item(_context([{"id": "calendar_event:e1", "summary": "Dentist morning"}, {"id": "calendar_event:e2", "summary": "Dentist evening"}]), "Dentist-i aç")


def test_resolve_item_rejects_missing_match():
    with pytest.raises(ResultResolutionError, match="tapılmadı"):
        resolve_item(_context([{"id": "calendar_event:e1", "summary": "Meeting"}]), "Dentist")


def test_resolve_item_rejects_empty_result():
    with pytest.raises(ResultResolutionError, match="boşdur"):
        resolve_item(_context([]), "Dentist")


def test_resolve_reference_uses_selected_item_for_pronoun():
    context = _context([{"id": "email:m1", "subject": "Birinci"}, {"id": "email:m2", "subject": "İkinci"}])
    item = resolve_reference(context, "ona", selected_item=context.data[1])
    assert item["id"] == "email:m2"


def test_resolve_reference_single_item_pronoun():
    item = resolve_reference(_context([{"id": "email:m1", "subject": "Bir email"}]), "o email")
    assert item["id"] == "email:m1"


def test_resolve_reference_ordinal():
    context = _context([
        {"id": "email:m1", "subject": "Birinci"},
        {"id": "email:m2", "subject": "İkinci"},
        {"id": "email:m3", "subject": "Üçüncü"},
    ])
    assert resolve_reference(context, "birincini")["id"] == "email:m1"
    assert resolve_reference(context, "ikincini")["id"] == "email:m2"
    assert resolve_reference(context, "üçüncünü")["id"] == "email:m3"


def test_resolve_reference_last_item():
    context = _context([{"id": "email:m1"}, {"id": "email:m2"}])
    assert resolve_reference(context, "sonuncunu")["id"] == "email:m2"


def test_resolve_reference_rejects_ambiguous_pronoun_without_selection():
    context = _context([{"id": "email:m1"}, {"id": "email:m2"}])
    with pytest.raises(ResultResolutionError, match="konkret nəticə"):
        resolve_reference(context, "bunu")


def test_resolve_reference_keeps_existing_named_resolution():
    context = _context([{"id": "email:m1", "subject": "Dentist"}, {"id": "email:m2", "subject": "Meeting"}])
    assert resolve_reference(context, "Dentist")["id"] == "email:m1"


def test_store_select_and_get_selected():
    store = ResultStore()
    result_id = store.save({"type": "calendar_event", "status": "success", "query": {}, "data": [{"id": "calendar_event:e1", "summary": "Dentist"}, {"id": "calendar_event:e2", "summary": "Meeting"}]})
    selected = store.select(result_id, "calendar_event:e1")
    assert selected["summary"] == "Dentist"
    assert store.selected()["id"] == "calendar_event:e1"


def test_store_select_rejects_unknown_item():
    store = ResultStore()
    result_id = store.save({"type": "contact", "status": "success", "query": {}, "data": [{"id": "contact:c1", "display_name": "Abu"}]})
    with pytest.raises(KeyError):
        store.select(result_id, "contact:missing")
