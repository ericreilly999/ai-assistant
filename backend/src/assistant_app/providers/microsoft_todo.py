from __future__ import annotations

from assistant_app.models import TaskItem


class MicrosoftToDoAdapter:
    key = "microsoft_todo"
    display_name = "Microsoft To Do"
    capabilities = ["tasks.read", "tasks.write", "grocery.read", "grocery.write"]

    def list_mock_tasks(self) -> list[TaskItem]:
        return [
            TaskItem(id="mstodo-1", title="Bread", source=self.key, status="notStarted", list_name="Groceries"),
            TaskItem(id="mstodo-2", title="Spinach", source=self.key, status="completed", list_name="Groceries"),
        ]

    def normalize_task(self, payload: dict) -> TaskItem:
        return TaskItem(
            id=payload["id"],
            title=payload.get("title", "Untitled task"),
            source=self.key,
            status=payload.get("status", "notStarted"),
            list_name=payload.get("list_name", "Tasks"),
            due=(payload.get("dueDateTime") or {}).get("dateTime"),
        )