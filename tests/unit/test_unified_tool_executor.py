import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.tool_executor import ToolExecutor


def test_query_unified_assistant_is_dispatched_to_orchestrator():
    ui = MagicMock()
    ui.muted = False
    executor = ToolExecutor(ui, MagicMock(), MagicMock(), MagicMock())
    fc = SimpleNamespace(
        id="unified-1",
        name="query_unified_assistant",
        args={"query": "Bu gün nə işim var?", "limit": 5},
    )
    unified = {
        "type": "unified_query",
        "status": "success",
        "query": {"text": "Bu gün nə işim var?"},
        "data": [{"id": "calendar:1", "source": "calendar", "title": "Meeting"}],
        "count": 1,
        "selected": None,
        "meta": {},
    }
    with patch("core.tool_executor.execute_unified_query", return_value=unified) as execute:
        response = asyncio.run(executor.execute(fc))

    execute.assert_called_once_with("Bu gün nə işim var?", 5)
    assert response.response["result"] == unified
