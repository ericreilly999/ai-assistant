from __future__ import annotations

import json
from pathlib import Path
import unittest

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