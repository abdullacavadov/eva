from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from core.result_context import ResultContext
from core.result_store import ResultStore


def _result(title="Dentist"):
    return {
        "type": "calendar_event",
        "status": "success",
        "query": {"date": "2026-08-20"},
        "data": [{"id": "calendar_event:e1", "summary": title}],
        "count": 1,
        "selected": None,
        "meta": {},
    }


def _context_result(intent="calendar_query", entity="Əhməd", selected_id=None, action=""):
    result = _result()
    result["query"]["intent"] = intent
    result["meta"] = {"entity": entity}
    if selected_id:
        result["meta"]["selected_id"] = selected_id
    if action:
        result["meta"]["action"] = action
    return result


def test_result_context_from_result():
    context = ResultContext.from_result("r1", _result(), 60)
    assert context.result_id == "r1"
    assert context.type == "calendar_event"
    assert context.data[0]["id"] == "calendar_event:e1"
    assert context.count == 1
    assert context.expires_at > context.created_at


def test_result_context_expiration():
    context = ResultContext.from_result("r1", _result(), 60)
    assert not context.is_expired(context.created_at + timedelta(seconds=59))
    assert context.is_expired(context.created_at + timedelta(seconds=60))


def test_store_save_get_and_current():
    store = ResultStore()
    result_id = store.save(_result())
    context = store.get(result_id)
    assert context is not None
    assert context.result_id == result_id
    assert store.current() == context


def test_store_current_tracks_latest_result():
    store = ResultStore()
    first = store.save(_result("First"))
    second = store.save(_result("Second"))
    assert store.current().result_id == second
    assert store.get(first).data[0]["summary"] == "First"


def test_store_clear():
    store = ResultStore()
    store.save(_result())
    store.clear()
    assert store.current() is None


def test_store_expires_results():
    store = ResultStore(ttl_seconds=1)
    result_id = store.save(_result())
    context = store.get(result_id)
    assert context is not None
    expired = replace(context, expires_at=context.created_at)
    store._results[result_id] = expired
    assert store.get(result_id) is None


def test_store_enforces_max_results():
    store = ResultStore(max_results=2)
    first = store.save(_result("First"))
    second = store.save(_result("Second"))
    third = store.save(_result("Third"))
    assert store.get(first) is None
    assert store.get(second) is not None
    assert store.get(third) is not None


def test_store_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        ResultStore(ttl_seconds=0)
    with pytest.raises(ValueError):
        ResultStore(max_results=0)


def test_store_captures_conversation_context_from_structured_result():
    store = ResultStore()
    result_id = store.save(_context_result())

    context = store.conversation()

    assert context is not None
    assert context.result_id == result_id
    assert context.intent == "calendar_query"
    assert context.entity == "Əhməd"
    assert context.selected_id is None
    assert context.action == ""


def test_store_selection_updates_conversation_context():
    store = ResultStore()
    result_id = store.save(_context_result())

    store.select(result_id, "calendar_event:e1")

    context = store.conversation()
    assert context is not None
    assert context.selected_id == "calendar_event:e1"


def test_store_conversation_context_can_track_action():
    store = ResultStore()
    store.save(_context_result())

    context = store.update_conversation(action="prepare_email_reply")

    assert context.action == "prepare_email_reply"
    assert context.intent == "calendar_query"
    assert context.entity == "Əhməd"


def test_store_conversation_context_expires_with_result_ttl():
    store = ResultStore(ttl_seconds=60)
    store.save(_context_result())
    current = store.conversation()
    assert current is not None

    future = (current.updated_at or datetime.now(timezone.utc)) + timedelta(seconds=60)
    assert store.conversation(now=future) is None


def test_store_clear_also_clears_conversation_context():
    store = ResultStore()
    store.save(_context_result())
    store.clear()

    assert store.conversation() is None
