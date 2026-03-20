from __future__ import annotations

from assistant_app.models import TaskItem


class GoogleTasksAdapter:
    key = "google_tasks"
    display_name = "Google Tasks"
    capabilities = ["tasks.read", "tasks.write", "grocery.read", "grocery.write"]

    def list_mock_tasks(self) -> list[TaskItem]:
        return [
            TaskItem(id="gtask-1", title="Milk", source=self.key, status="needsAction", list_name="Groceries"),
            TaskItem(id="gtask-2", title="Eggs", source=self.key, status="completed", list_name="Groceries"),
        ]

    def normalize_task(self, payload: dict) -> TaskItem:
        return TaskItem(
            id=payload["id"],
            title=payload.get("title", "Untitled task"),
            source=self.key,
            status=payload.get("status", "needsAction"),
            list_name=payload.get("list_name", "Tasks"),
            due=payload.get("due"),
        )