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

    def normalize_update_task_payload(self, task_id: str, updates: dict) -> dict:
        """Convert a user-friendly updates dict to a Microsoft Graph To Do patch body."""
        body: dict = {}
        if "title" in updates:
            body["title"] = updates["title"]
        if "due" in updates:
            body["dueDateTime"] = {"dateTime": updates["due"], "timeZone": "UTC"}
        if "notes" in updates:
            body["body"] = {"content": updates["notes"], "contentType": "text"}
        if "status" in updates:
            body["status"] = updates["status"]
        return body

    def update_task(self, list_id: str, task_id: str, updates: dict) -> dict:
        """Return a normalized patch body for a Microsoft To Do update (caller does HTTP)."""
        return self.normalize_update_task_payload(task_id, updates)

    def complete_task(self, list_id: str, task_id: str) -> dict:
        """Return a normalized patch body to mark a task completed (caller does HTTP)."""
        return {"status": "completed"}
