from unittest.mock import patch

from actions.reminders import add_reminder, get_reminders


@patch("actions.reminders.resolve_task_list_id", return_value="default")
@patch("actions.reminders.list_tasks")
def test_get_reminders(mock_list_tasks, mock_resolve):
    mock_list_tasks.return_value = [
        {"id": "1", "title": "Buy milk", "due": "2026-08-20T10:00:00Z"}
    ]

    result = get_reminders("upcoming", 8, "Work")

    mock_resolve.assert_called_once_with("Work")
    assert "Buy milk" in result
    assert "Google Tasks" in result


def test_get_reminders_filters_text_query():
    with patch("actions.reminders.resolve_task_list_id", return_value="default"), patch(
        "actions.reminders.list_tasks",
        return_value=[
            {"title": "Buy milk"},
            {"title": "Call Ahmed"},
        ],
    ):
        result = get_reminders("Ahmed", 8, "")

    assert "Call Ahmed" in result
    assert "Buy milk" not in result


def test_get_reminders_filters_before_applying_limit():
    tasks = [{"title": f"Noise {index}"} for index in range(8)]
    tasks.append({"title": "Call Ahmed"})

    with patch("actions.reminders.resolve_task_list_id", return_value="default"), patch(
        "actions.reminders.list_tasks", return_value=tasks
    ) as mock_list_tasks:
        result = get_reminders("Ahmed", 1, "")

    mock_list_tasks.assert_called_once_with(
        task_list_id="default",
        max_results=100,
        show_completed=False,
    )
    assert "Call Ahmed" in result


def test_add_reminder_rejects_empty_title():
    with patch("actions.reminders.create_task") as mock_create:
        result = add_reminder("")

    mock_create.assert_not_called()
    assert "boş" in result


def test_add_reminder_rejects_invalid_due():
    with patch("actions.reminders.create_task") as mock_create:
        result = add_reminder("Test", "not-a-date")

    mock_create.assert_not_called()
    assert "yanlışdır" in result


def test_add_reminder_rejects_priority():
    with patch("actions.reminders.create_task") as mock_create:
        result = add_reminder("Test", priority="high")

    mock_create.assert_not_called()
    assert "priority" in result


@patch("actions.reminders.resolve_task_list_id", return_value="default")
@patch("actions.reminders.create_task")
def test_add_reminder_creates_task(mock_create, mock_resolve):
    mock_create.return_value = {"title": "Test"}

    result = add_reminder(
        "Test",
        due_iso="2026-08-20T10:00:00+04:00",
        notes="Note",
        list_name="Work",
    )

    mock_resolve.assert_called_once_with("Work")
    mock_create.assert_called_once_with(
        title="Test",
        due_iso="2026-08-20T10:00:00+04:00",
        notes="Note",
        task_list_id="default",
    )
    assert "əlavə edildi" in result
