from __future__ import annotations

import json
import unittest
from pathlib import Path

from assistant_app.providers.google_calendar import GoogleCalendarAdapter
from assistant_app.providers.google_drive import GoogleDriveAdapter
from assistant_app.providers.google_tasks import GoogleTasksAdapter
from assistant_app.providers.microsoft_calendar import MicrosoftCalendarAdapter
from assistant_app.providers.microsoft_todo import MicrosoftToDoAdapter
from assistant_app.providers.plaid import PlaidAdapter

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class ProviderNormalizationTests(unittest.TestCase):
    def test_google_calendar_normalization(self) -> None:
        event = GoogleCalendarAdapter().normalize_event(load_fixture("google_calendar_event.json"))
        self.assertEqual(event.title, "Team sync")
        self.assertEqual(event.reminder_minutes, 30)
        self.assertEqual(event.location, "Zoom")

    def test_google_tasks_normalization(self) -> None:
        task = GoogleTasksAdapter().normalize_task(load_fixture("google_task.json"))
        self.assertEqual(task.list_name, "Groceries")
        self.assertEqual(task.status, "needsAction")

    def test_google_drive_normalization(self) -> None:
        document = GoogleDriveAdapter().normalize_file(load_fixture("google_drive_file.json"))
        self.assertEqual(document.title, "Architecture Review Notes")
        self.assertTrue(document.web_view_link)

    def test_microsoft_calendar_normalization(self) -> None:
        event = MicrosoftCalendarAdapter().normalize_event(load_fixture("microsoft_event.json"))
        self.assertEqual(event.title, "Architecture review")
        self.assertEqual(event.reminder_minutes, 10)
        self.assertEqual(event.location, "Conference Room")

    def test_microsoft_todo_normalization(self) -> None:
        task = MicrosoftToDoAdapter().normalize_task(load_fixture("microsoft_todo.json"))
        self.assertEqual(task.list_name, "Groceries")
        self.assertEqual(task.status, "notStarted")

    def test_plaid_normalization(self) -> None:
        account = PlaidAdapter().normalize_account(load_fixture("plaid_account.json"))
        self.assertEqual(account.mask, "1234")
        self.assertEqual(account.available_balance, 1580.25)


class GoogleTasksMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = GoogleTasksAdapter()

    def test_update_task_patch_body_title(self) -> None:
        body = self.adapter.update_task("list-1", "task-1", {"title": "New title"})
        self.assertEqual(body["title"], "New title")

    def test_update_task_patch_body_status(self) -> None:
        body = self.adapter.update_task("list-1", "task-1", {"status": "completed"})
        self.assertEqual(body["status"], "completed")

    def test_complete_task_sets_completed_status(self) -> None:
        body = self.adapter.complete_task("list-1", "task-1")
        self.assertEqual(body["status"], "completed")

    def test_list_mock_tasks_returns_items(self) -> None:
        tasks = self.adapter.list_mock_tasks()
        self.assertGreater(len(tasks), 0)
        self.assertEqual(tasks[0].source, "google_tasks")

    def test_normalize_task_missing_optional_fields(self) -> None:
        task = self.adapter.normalize_task({"id": "t-1", "title": "Do something"})
        self.assertEqual(task.id, "t-1")
        self.assertIsNone(task.due)


class MicrosoftToDoMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = MicrosoftToDoAdapter()

    def test_update_task_patch_body_title(self) -> None:
        body = self.adapter.update_task("list-1", "task-1", {"title": "New title"})
        self.assertEqual(body["title"], "New title")

    def test_update_task_due_converts_to_graph_format(self) -> None:
        body = self.adapter.update_task("list-1", "task-1", {"due": "2026-05-01T00:00:00"})
        self.assertIn("dueDateTime", body)
        self.assertEqual(body["dueDateTime"]["dateTime"], "2026-05-01T00:00:00")

    def test_complete_task_sets_completed_status(self) -> None:
        body = self.adapter.complete_task("list-1", "task-1")
        self.assertEqual(body["status"], "completed")

    def test_list_mock_tasks_returns_items(self) -> None:
        tasks = self.adapter.list_mock_tasks()
        self.assertGreater(len(tasks), 0)
        self.assertEqual(tasks[0].source, "microsoft_todo")

    def test_normalize_task_missing_due_datetime(self) -> None:
        task = self.adapter.normalize_task({"id": "t-1", "title": "Do something", "status": "notStarted"})
        self.assertIsNone(task.due)


class GoogleCalendarMockTests(unittest.TestCase):
    def test_list_mock_events_returns_expected_count(self) -> None:
        events = GoogleCalendarAdapter().list_mock_events()
        self.assertGreater(len(events), 0)

    def test_normalize_event_all_day_date_fallback(self) -> None:
        payload = {
            "id": "evt-1",
            "summary": "All-day event",
            "start": {"date": "2026-05-01"},
            "end": {"date": "2026-05-02"},
        }
        event = GoogleCalendarAdapter().normalize_event(payload)
        self.assertEqual(event.start, "2026-05-01")


class MicrosoftCalendarMockTests(unittest.TestCase):
    def test_list_mock_events(self) -> None:
        events = MicrosoftCalendarAdapter().list_mock_events()
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].source, "microsoft_calendar")
