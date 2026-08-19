from unittest.mock import MagicMock, patch

from integrations.google.tasks import (
    create_task,
    list_task_lists,
    list_tasks,
    resolve_task_list_id,
)


def mock_service():
    return MagicMock()


@patch("integrations.google.tasks.get_tasks_service")
def test_list_task_lists(mock_get_service):
    service = mock_service()
    service.tasklists.return_value.list.return_value.execute.side_effect = [
        {"items": [{"id": "default", "title": "My Tasks"}]}
    ]
    mock_get_service.return_value = service

    assert list_task_lists() == [{"id": "default", "title": "My Tasks"}]


@patch("integrations.google.tasks.list_task_lists")
def test_resolve_task_list_id(mock_list):
    mock_list.return_value = [
        {"id": "default", "title": "My Tasks"},
        {"id": "work", "title": "Work"},
    ]

    assert resolve_task_list_id("work") == "work"
    assert resolve_task_list_id("") == "@default"


@patch("integrations.google.tasks.get_tasks_service")
def test_list_tasks(mock_get_service):
    service = mock_service()
    service.tasks.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "task-1", "title": "Test"}]
    }
    mock_get_service.return_value = service

    result = list_tasks("default", max_results=5)

    assert result == [{"id": "task-1", "title": "Test"}]
    service.tasks.return_value.list.assert_called_once_with(
        tasklist="default",
        maxResults=5,
        showCompleted=False,
        showHidden=False,
    )


@patch("integrations.google.tasks.get_tasks_service")
def test_list_tasks_follows_pagination_until_limit(mock_get_service):
    service = mock_service()
    service.tasks.return_value.list.return_value.execute.side_effect = [
        {
            "items": [{"id": "task-1", "title": "First"}],
            "nextPageToken": "page-2",
        },
        {
            "items": [{"id": "task-2", "title": "Second"}],
        },
    ]
    mock_get_service.return_value = service

    result = list_tasks("default", max_results=2)

    assert result == [
        {"id": "task-1", "title": "First"},
        {"id": "task-2", "title": "Second"},
    ]
    calls = service.tasks.return_value.list.call_args_list
    assert calls[0].kwargs == {
        "tasklist": "default",
        "maxResults": 2,
        "showCompleted": False,
        "showHidden": False,
    }
    assert calls[1].kwargs == {
        "tasklist": "default",
        "maxResults": 1,
        "showCompleted": False,
        "showHidden": False,
        "pageToken": "page-2",
    }


@patch("integrations.google.tasks.get_tasks_service")
def test_create_task(mock_get_service):
    service = mock_service()
    service.tasks.return_value.insert.return_value.execute.return_value = {
        "id": "task-1",
        "title": "Test",
    }
    mock_get_service.return_value = service

    result = create_task(
        title="Test",
        due_iso="2026-08-20T10:00:00+04:00",
        notes="Note",
        task_list_id="default",
    )

    assert result["id"] == "task-1"
    service.tasks.return_value.insert.assert_called_once_with(
        tasklist="default",
        body={
            "title": "Test",
            "notes": "Note",
            "due": "2026-08-20T06:00:00Z",
        },
    )
