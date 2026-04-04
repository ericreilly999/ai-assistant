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

    def normalize_update_task_payload(self, task_id: str, updates: dict) -> dict:
        """Convert a user-friendly updates dict to a Google Tasks API patch body."""
        body: dict = {}
        if "title" in updates:
            body["title"] = updates["title"]
        if "due" in updates:
            body["due"] = updates["due"]
        if "notes" in updates:
            body["notes"] = updates["notes"]
        if "status" in updates:
            body["status"] = updates["status"]
        return body

    def update_task(self, list_id: str, task_id: str, updates: dict) -> dict:
        """Return a normalized patch body for a Google Tasks update (caller does HTTP)."""
        return self.normalize_update_task_payload(task_id, updates)

    def complete_task(self, list_id: str, task_id: str) -> dict:
        """Return a normalized patch body to mark a task completed (caller does HTTP)."""
        return {"status": "completed", "hidden": True}
