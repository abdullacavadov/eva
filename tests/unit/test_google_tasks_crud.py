from unittest.mock import MagicMock, patch

from integrations.google.tasks import complete_task, delete_task, update_task


def test_update_task_patches_only_provided_fields():
    service = MagicMock()
    service.tasks().patch.return_value.execute.return_value = {"id": "1", "title": "Updated"}
    with patch("integrations.google.tasks.get_tasks_service", return_value=service):
        result = update_task("1", title="Updated")
    service.tasks().patch.assert_called_once_with(tasklist="@default", task="1", body={"title": "Updated"})
    assert result["title"] == "Updated"


def test_complete_task_sets_completed_status():
    service = MagicMock()
    service.tasks().patch.return_value.execute.return_value = {"id": "1", "status": "completed"}
    with patch("integrations.google.tasks.get_tasks_service", return_value=service):
        result = complete_task("1", "work")
    service.tasks().patch.assert_called_once_with(tasklist="work", task="1", body={"status": "completed"})
    assert result["status"] == "completed"


def test_delete_task_calls_google_delete():
    service = MagicMock()
    with patch("integrations.google.tasks.get_tasks_service", return_value=service):
        delete_task("1", "work")
    service.tasks().delete.assert_called_once_with(tasklist="work", task="1")
    service.tasks().delete.return_value.execute.assert_called_once_with()
