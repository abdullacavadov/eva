import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.tool_executor import ToolExecutor


def make_executor():
    ui = MagicMock()
    ui.muted = False
    webcam = MagicMock()
    focus = MagicMock()
    speak_error = MagicMock()
    executor = ToolExecutor(ui, webcam, focus, speak_error)
    return executor, ui, webcam, focus, speak_error


def test_result_looks_like_error():
    assert ToolExecutor.result_looks_like_error("Xəta: bağlantı alınmadı") is True
    assert ToolExecutor.result_looks_like_error("Əməliyyat uğurla tamamlandı") is False


def test_success_sfx_for_calendar_action():
    assert ToolExecutor.should_play_success_sfx(
        "add_calendar_event", {}, "Tədbir əlavə edildi."
    ) is True


def test_success_sfx_for_whatsapp_send():
    assert ToolExecutor.should_play_success_sfx(
        "send_whatsapp_message",
        {"send_now": True},
        "Mesaj göndərildi.",
    ) is True


def test_memory_tools_do_not_play_success_sfx():
    assert ToolExecutor.should_play_success_sfx("save_memory", {}, "ok") is False
    assert ToolExecutor.should_play_success_sfx(
        "delete_memory", {}, "profile/name hafizadan kaldirildi."
    ) is False


def test_unknown_tool_returns_function_response():
    executor, ui, *_ = make_executor()
    fc = SimpleNamespace(id="call-1", name="unknown_tool", args={})

    response = asyncio.run(executor.execute(fc))

    assert response.id == "call-1"
    assert response.name == "unknown_tool"
    assert response.response["result"] == "Naməlum alət: unknown_tool"
    ui.set_state.assert_any_call("THINKING")


@patch("core.tool_executor.open_app", return_value="Notepad açıldı.")
def test_open_app_is_dispatched_to_action(mock_open_app):
    executor, ui, *_ = make_executor()
    fc = SimpleNamespace(
        id="call-2",
        name="open_app",
        args={"app_name": "notepad"},
    )

    response = asyncio.run(executor.execute(fc))

    assert response.response["result"] == "Notepad açıldı."
    mock_open_app.assert_called_once_with("notepad")
    ui.play_success_sfx.assert_called_once()


def test_action_exception_is_converted_to_error_response():
    executor, ui, _, _, speak_error = make_executor()
    fc = SimpleNamespace(id="call-3", name="open_app", args={"app_name": "notepad"})

    with patch("core.tool_executor.open_app", side_effect=RuntimeError("test xətası")):
        response = asyncio.run(executor.execute(fc))

    assert "Xəta: test xətası" == response.response["result"]
    speak_error.assert_called_once()
    ui.set_state.assert_any_call("ERROR")


@patch("core.tool_executor.update_memory")
def test_save_memory_dispatches_expected_payload(mock_update_memory):
    executor, *_ = make_executor()
    fc = SimpleNamespace(
        id="memory-save-1",
        name="save_memory",
        args={"category": "profile", "key": "name", "value": "Abdulla"},
    )

    response = asyncio.run(executor.execute(fc))

    mock_update_memory.assert_called_once_with(
        {"profile": {"name": {"value": "Abdulla"}}}
    )
    assert response.id == "memory-save-1"
    assert response.name == "save_memory"
    assert response.response["result"] == "ok"


@patch("core.tool_executor.update_memory")
def test_save_memory_invalid_arguments_must_not_report_success(mock_update_memory):
    executor, *_ = make_executor()
    fc = SimpleNamespace(
        id="memory-save-2",
        name="save_memory",
        args={"category": "profile", "key": "", "value": "Abdulla"},
    )

    response = asyncio.run(executor.execute(fc))

    mock_update_memory.assert_not_called()
    assert response.response["result"] != "ok"


@patch("core.tool_executor.update_memory", side_effect=RuntimeError("disk error"))
def test_save_memory_exception_is_converted_to_error_response(mock_update_memory):
    executor, ui, _, _, speak_error = make_executor()
    fc = SimpleNamespace(
        id="memory-save-3",
        name="save_memory",
        args={"category": "profile", "key": "name", "value": "Abdulla"},
    )

    response = asyncio.run(executor.execute(fc))

    assert response.response["result"] == "Xəta: disk error"
    mock_update_memory.assert_called_once()
    speak_error.assert_called_once()
    ui.set_state.assert_any_call("ERROR")


@patch("core.tool_executor.delete_memory", return_value="profile/name hafizadan kaldirildi.")
def test_delete_memory_dispatches_all_arguments(mock_delete_memory):
    executor, *_ = make_executor()
    fc = SimpleNamespace(
        id="memory-delete-1",
        name="delete_memory",
        args={
            "category": "profile",
            "key": "name",
            "match_text": "",
        },
    )

    response = asyncio.run(executor.execute(fc))

    mock_delete_memory.assert_called_once_with("profile", "name", "")
    assert response.response["result"] == "profile/name hafizadan kaldirildi."


@patch("core.tool_executor.delete_memory", return_value="Bu hafiza kaydini bulamadim.")
def test_delete_memory_propagates_not_found_result(mock_delete_memory):
    executor, *_ = make_executor()
    fc = SimpleNamespace(
        id="memory-delete-2",
        name="delete_memory",
        args={"category": "profile", "key": "missing", "match_text": ""},
    )

    response = asyncio.run(executor.execute(fc))

    assert response.response["result"] == "Bu hafiza kaydini bulamadim."
    mock_delete_memory.assert_called_once_with("profile", "missing", "")


@patch("core.tool_executor.delete_memory", side_effect=RuntimeError("disk error"))
def test_delete_memory_exception_is_converted_to_error_response(mock_delete_memory):
    executor, ui, _, _, speak_error = make_executor()
    fc = SimpleNamespace(
        id="memory-delete-3",
        name="delete_memory",
        args={"category": "profile", "key": "name", "match_text": ""},
    )

    response = asyncio.run(executor.execute(fc))

    assert response.response["result"] == "Xəta: disk error"
    mock_delete_memory.assert_called_once_with("profile", "name", "")
    speak_error.assert_called_once()
    ui.set_state.assert_any_call("ERROR")
