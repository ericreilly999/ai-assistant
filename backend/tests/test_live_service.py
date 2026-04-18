"""Tests for live_service.py.

Coverage targets (module previously at 41%):
  LocalIntegrationService.connection_status()
  google_auth_url() / complete_google_auth()
  microsoft_auth_url() / complete_microsoft_auth()
  list_google_calendar_events() / create_google_calendar_event()
  list_google_tasklists() / list_google_tasks() / add_google_grocery_items()
  _resolve_google_tasklist_id()
  list_google_drive_documents() / export_google_drive_document()
  list_microsoft_calendar_events() / create_microsoft_calendar_event()
  list_microsoft_tasklists() / list_microsoft_tasks() / add_microsoft_grocery_items()
  _resolve_ms_tasklist_id()
  bootstrap_plaid_sandbox() / list_plaid_accounts() / list_plaid_transactions()
  _plaid_base() environment branching
  update_google_task() / complete_google_task()
  update_microsoft_task() / complete_microsoft_task()
  get_drive_documents_for_event()
  _google_token() / _ms_token() raise on missing token
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from assistant_app.config import AppConfig
from assistant_app.live_service import LocalIntegrationService
from assistant_app.registry import ProviderRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> AppConfig:
    defaults = {
        "app_env": "dev",
        "log_level": "INFO",
        "mock_provider_mode": False,
        "proposal_ttl_minutes": 15,
        "default_timezone": "America/New_York",
        "bedrock_router_model_id": "mock-router",
        "bedrock_guardrail_id": "mock-guardrail",
        "bedrock_guardrail_version": "DRAFT",
        "google_client_id": "google-client-id",
        "google_client_secret": "google-secret",
        "google_redirect_uri": "http://localhost/callback/google",
        "microsoft_client_id": "ms-client-id",
        "microsoft_client_secret": "ms-secret",
        "microsoft_redirect_uri": "http://localhost/callback/ms",
        "plaid_client_id": "plaid-client",
        "plaid_secret": "plaid-secret",
        "plaid_env": "sandbox",
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


def _make_service(store_overrides: dict | None = None, config_overrides: dict | None = None) -> LocalIntegrationService:
    """Return a LocalIntegrationService with a mocked DevTokenStore."""
    config = _make_config(**(config_overrides or {}))
    registry = ProviderRegistry(mock_mode=True)
    svc = LocalIntegrationService(config, registry)

    # Replace the token store with a mock so tests never touch the filesystem.
    mock_store = MagicMock()
    mock_store.get_tokens.return_value = None
    mock_store.expires_at.return_value = None
    mock_store.plaid_status.return_value = {"connected": False}
    if store_overrides:
        for attr, val in store_overrides.items():
            setattr(mock_store, attr, val)
    svc._store = mock_store
    return svc


# ---------------------------------------------------------------------------
# connection_status
# ---------------------------------------------------------------------------

class TestConnectionStatus(unittest.TestCase):

    def test_returns_disconnected_when_no_tokens(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.return_value = None
        svc._store.plaid_status.return_value = {"connected": False}

        status = svc.connection_status()

        self.assertFalse(status["google"]["connected"])
        self.assertFalse(status["microsoft"]["connected"])
        self.assertFalse(status["plaid"]["connected"])

    def test_returns_connected_when_google_has_access_token(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.side_effect = lambda key: (
            {"access_token": "goog-tok"} if key == "google" else None
        )
        status = svc.connection_status()
        self.assertTrue(status["google"]["connected"])

    def test_returns_connected_when_microsoft_has_access_token(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.side_effect = lambda key: (
            {"access_token": "ms-tok"} if key == "microsoft" else None
        )
        status = svc.connection_status()
        self.assertTrue(status["microsoft"]["connected"])

    def test_plaid_status_comes_from_store(self) -> None:
        svc = _make_service()
        svc._store.plaid_status.return_value = {"connected": True, "institution_id": "chase"}
        status = svc.connection_status()
        self.assertTrue(status["plaid"]["connected"])


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

class TestGoogleAuthUrl(unittest.TestCase):

    def test_returns_google_auth_url_containing_client_id(self) -> None:
        svc = _make_service()
        url = svc.google_auth_url()
        self.assertIn("google-client-id", url)
        self.assertIn("accounts.google.com", url)

    def test_raises_when_google_client_id_not_configured(self) -> None:
        svc = _make_service(config_overrides={"google_client_id": ""})
        with self.assertRaises(ValueError) as ctx:
            svc.google_auth_url()
        self.assertIn("GOOGLE_CLIENT_ID", str(ctx.exception))

    def test_stores_oauth_state_in_token_store(self) -> None:
        svc = _make_service()
        svc.google_auth_url()
        svc._store.merge_tokens.assert_called_once()
        call_args = svc._store.merge_tokens.call_args
        self.assertEqual(call_args.args[0], "google_oauth_state")

    def test_url_includes_offline_access_and_consent(self) -> None:
        svc = _make_service()
        url = svc.google_auth_url()
        self.assertIn("offline", url)
        self.assertIn("consent", url)


class TestCompleteGoogleAuth(unittest.TestCase):

    def test_success_stores_tokens_and_returns_dict(self) -> None:
        svc = _make_service()
        fake_tokens = {"access_token": "goog-access", "refresh_token": "goog-refresh", "scope": "openid"}

        with patch("assistant_app.live_service.http_post_form", return_value=fake_tokens):
            result = svc.complete_google_auth("auth-code-xyz", "state-abc")

        svc._store.set_tokens.assert_called_once()
        self.assertEqual(result["provider"], "google")
        self.assertTrue(result["stored"])
        self.assertEqual(result["scope"], "openid")

    def test_raises_when_credentials_not_configured(self) -> None:
        svc = _make_service(config_overrides={"google_client_id": ""})
        with self.assertRaises(ValueError) as ctx:
            svc.complete_google_auth("code", "state")
        self.assertIn("Google OAuth", str(ctx.exception))


# ---------------------------------------------------------------------------
# Microsoft OAuth
# ---------------------------------------------------------------------------

class TestMicrosoftAuthUrl(unittest.TestCase):

    def test_returns_ms_auth_url_containing_client_id(self) -> None:
        svc = _make_service()
        url = svc.microsoft_auth_url()
        self.assertIn("ms-client-id", url)
        self.assertIn("microsoftonline.com", url)

    def test_raises_when_microsoft_client_id_not_configured(self) -> None:
        svc = _make_service(config_overrides={"microsoft_client_id": ""})
        with self.assertRaises(ValueError) as ctx:
            svc.microsoft_auth_url()
        self.assertIn("MICROSOFT_CLIENT_ID", str(ctx.exception))

    def test_stores_oauth_state_in_token_store(self) -> None:
        svc = _make_service()
        svc.microsoft_auth_url()
        svc._store.merge_tokens.assert_called_once()
        call_args = svc._store.merge_tokens.call_args
        self.assertEqual(call_args.args[0], "microsoft_oauth_state")


class TestCompleteMicrosoftAuth(unittest.TestCase):

    def test_success_stores_tokens_and_returns_dict(self) -> None:
        svc = _make_service()
        fake_tokens = {"access_token": "ms-access", "refresh_token": "ms-refresh", "scope": "Calendars.ReadWrite"}

        with patch("assistant_app.live_service.http_post_form", return_value=fake_tokens):
            result = svc.complete_microsoft_auth("auth-code-ms", "state-ms")

        svc._store.set_tokens.assert_called_once()
        self.assertEqual(result["provider"], "microsoft")
        self.assertTrue(result["stored"])

    def test_raises_when_credentials_not_configured(self) -> None:
        svc = _make_service(config_overrides={"microsoft_client_id": ""})
        with self.assertRaises(ValueError) as ctx:
            svc.complete_microsoft_auth("code", "state")
        self.assertIn("Microsoft OAuth", str(ctx.exception))


# ---------------------------------------------------------------------------
# _google_token / _ms_token raise when disconnected
# ---------------------------------------------------------------------------

class TestTokenRaiseWhenDisconnected(unittest.TestCase):

    def test_google_token_raises_when_not_connected(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.return_value = {}
        with self.assertRaises(ValueError) as ctx:
            svc._google_token()
        self.assertIn("Google is not connected", str(ctx.exception))

    def test_ms_token_raises_when_not_connected(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.return_value = {}
        with self.assertRaises(ValueError) as ctx:
            svc._ms_token()
        self.assertIn("Microsoft is not connected", str(ctx.exception))

    def test_google_token_raises_when_tokens_none(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.return_value = None
        with self.assertRaises(ValueError):
            svc._google_token()

    def test_ms_token_raises_when_tokens_none(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.return_value = None
        with self.assertRaises(ValueError):
            svc._ms_token()


# ---------------------------------------------------------------------------
# Google Calendar
# ---------------------------------------------------------------------------

def _google_store(token: str = "goog-tok") -> MagicMock:
    store = MagicMock()
    store.get_tokens.return_value = {"access_token": token}
    store.expires_at.return_value = None
    store.plaid_status.return_value = {"connected": False}
    return store


class TestGoogleCalendarEvents(unittest.TestCase):

    def test_list_events_returns_events_list(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw_event = {
            "id": "evt-001",
            "summary": "Team Standup",
            "start": {"dateTime": "2026-04-20T09:00:00-04:00"},
            "end": {"dateTime": "2026-04-20T09:30:00-04:00"},
        }
        raw_response = {"items": [raw_event]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_google_calendar_events("2026-04-20T00:00:00Z", "2026-04-20T23:59:59Z")

        self.assertIn("events", result)
        self.assertEqual(result["provider"], "google_calendar")
        self.assertEqual(len(result["events"]), 1)

    def test_list_events_with_no_start_end(self) -> None:
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_get", return_value={"items": []}):
            result = svc.list_google_calendar_events(None, None)

        self.assertEqual(result["events"], [])

    def test_create_event_returns_event_dict(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw_event = {
            "id": "new-evt",
            "summary": "New Meeting",
            "start": {"dateTime": "2026-04-21T10:00:00-04:00"},
            "end": {"dateTime": "2026-04-21T11:00:00-04:00"},
        }

        with patch("assistant_app.live_service.http_post", return_value=raw_event):
            result = svc.create_google_calendar_event(raw_event)

        self.assertIn("event", result)
        self.assertEqual(result["provider"], "google_calendar")


# ---------------------------------------------------------------------------
# Google Tasks
# ---------------------------------------------------------------------------

class TestGoogleTasks(unittest.TestCase):

    def test_list_tasklists_returns_lists(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw_response = {"items": [{"id": "list-1", "title": "Groceries"}]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_google_tasklists()

        self.assertEqual(result["provider"], "google_tasks")
        self.assertEqual(len(result["task_lists"]), 1)
        self.assertEqual(result["task_lists"][0]["id"], "list-1")

    def test_list_tasks_returns_tasks(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw_task = {
            "id": "task-1",
            "title": "Buy milk",
            "status": "needsAction",
            "due": None,
        }
        raw_response = {"items": [raw_task]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_google_tasks("list-1", None)

        self.assertEqual(result["provider"], "google_tasks")
        self.assertEqual(len(result["tasks"]), 1)

    def test_add_grocery_items_returns_created_count(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        list_response = {"items": [{"id": "list-groc", "title": "Groceries"}]}

        with patch("assistant_app.live_service.http_get", return_value=list_response), patch("assistant_app.live_service.http_post", return_value={"id": "new-task"}):
            result = svc.add_google_grocery_items({
                "list_name": "Groceries",
                "items": ["milk", "eggs"],
            })

        self.assertEqual(result["created_count"], 2)
        self.assertEqual(result["provider"], "google_tasks")

    def test_resolve_tasklist_id_matches_by_name(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw = {"items": [
            {"id": "list-a", "title": "Work"},
            {"id": "list-b", "title": "Groceries"},
        ]}

        with patch("assistant_app.live_service.http_get", return_value=raw):
            result = svc._resolve_google_tasklist_id("Groceries")

        self.assertEqual(result, "list-b")

    def test_resolve_tasklist_id_falls_back_to_first_when_no_match(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw = {"items": [{"id": "list-a", "title": "Work"}]}

        with patch("assistant_app.live_service.http_get", return_value=raw):
            result = svc._resolve_google_tasklist_id("NonExistentList")

        self.assertEqual(result, "list-a")

    def test_resolve_tasklist_id_raises_when_no_lists(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        with patch("assistant_app.live_service.http_get", return_value={"items": []}), self.assertRaises(ValueError) as ctx:
            svc._resolve_google_tasklist_id("Groceries")
        self.assertIn("No task list found", str(ctx.exception))


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

class TestGoogleDrive(unittest.TestCase):

    def test_list_drive_documents_returns_documents(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw_file = {
            "id": "file-1",
            "name": "Architecture Review",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/doc/file-1",
        }
        raw_response = {"files": [raw_file]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_google_drive_documents(None)

        self.assertEqual(result["provider"], "google_drive")
        self.assertEqual(len(result["documents"]), 1)

    def test_export_drive_document_returns_content(self) -> None:
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_get_text", return_value="Document content here"):
            result = svc.export_google_drive_document("file-1", "text/plain")

        self.assertEqual(result["file_id"], "file-1")
        self.assertEqual(result["mime_type"], "text/plain")
        self.assertIn("content", result)

    def test_export_drive_document_truncates_content_to_4000_chars(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        long_content = "A" * 10000

        with patch("assistant_app.live_service.http_get_text", return_value=long_content):
            result = svc.export_google_drive_document("file-1", "text/plain")

        self.assertLessEqual(len(result["content"]), 4000)


# ---------------------------------------------------------------------------
# Microsoft Calendar
# ---------------------------------------------------------------------------

def _ms_store(token: str = "ms-tok") -> MagicMock:
    store = MagicMock()
    store.get_tokens.return_value = {"access_token": token}
    store.expires_at.return_value = None
    store.plaid_status.return_value = {"connected": False}
    return store


class TestMicrosoftCalendarEvents(unittest.TestCase):

    def test_list_events_returns_events(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw_event = {
            "id": "ms-evt-1",
            "subject": "Sprint Planning",
            "start": {"dateTime": "2026-04-20T10:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-04-20T11:00:00", "timeZone": "UTC"},
        }
        raw_response = {"value": [raw_event]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_microsoft_calendar_events(None, None)

        self.assertEqual(result["provider"], "microsoft_calendar")
        self.assertEqual(len(result["events"]), 1)

    def test_create_event_returns_event_dict(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw_event = {
            "id": "ms-new-evt",
            "subject": "New Meeting",
            "start": {"dateTime": "2026-04-21T14:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-04-21T15:00:00", "timeZone": "UTC"},
        }

        with patch("assistant_app.live_service.http_post", return_value=raw_event):
            result = svc.create_microsoft_calendar_event(raw_event)

        self.assertIn("event", result)
        self.assertEqual(result["provider"], "microsoft_calendar")


# ---------------------------------------------------------------------------
# Microsoft To Do
# ---------------------------------------------------------------------------

class TestMicrosoftTasks(unittest.TestCase):

    def test_list_tasklists_returns_lists(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw_response = {"value": [{"id": "ms-list-1", "displayName": "Groceries"}]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_microsoft_tasklists()

        self.assertEqual(result["provider"], "microsoft_todo")
        self.assertEqual(len(result["task_lists"]), 1)

    def test_list_tasks_returns_tasks(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw_task = {
            "id": "ms-task-1",
            "title": "Buy bread",
            "status": "notStarted",
        }
        raw_response = {"value": [raw_task]}

        with patch("assistant_app.live_service.http_get", return_value=raw_response):
            result = svc.list_microsoft_tasks("ms-list-1", None)

        self.assertEqual(result["provider"], "microsoft_todo")
        self.assertEqual(len(result["tasks"]), 1)

    def test_add_grocery_items_returns_created_count(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        list_response = {"value": [{"id": "ms-list-groc", "displayName": "Groceries"}]}

        with patch("assistant_app.live_service.http_get", return_value=list_response), patch("assistant_app.live_service.http_post", return_value={"id": "new-ms-task"}):
            result = svc.add_microsoft_grocery_items({
                "list_name": "Groceries",
                "items": ["milk", "eggs", "butter"],
            })

        self.assertEqual(result["created_count"], 3)
        self.assertEqual(result["provider"], "microsoft_todo")

    def test_resolve_ms_tasklist_id_matches_by_name(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw = {"value": [
            {"id": "ms-a", "displayName": "Work"},
            {"id": "ms-b", "displayName": "Groceries"},
        ]}

        with patch("assistant_app.live_service.http_get", return_value=raw):
            result = svc._resolve_ms_tasklist_id("Groceries")

        self.assertEqual(result, "ms-b")

    def test_resolve_ms_tasklist_id_falls_back_to_first_when_no_match(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw = {"value": [{"id": "ms-a", "displayName": "Work"}]}

        with patch("assistant_app.live_service.http_get", return_value=raw):
            result = svc._resolve_ms_tasklist_id("Nonexistent")

        self.assertEqual(result, "ms-a")

    def test_resolve_ms_tasklist_id_raises_when_no_lists(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        with patch("assistant_app.live_service.http_get", return_value={"value": []}), self.assertRaises(ValueError) as ctx:
            svc._resolve_ms_tasklist_id("Groceries")
        self.assertIn("No Microsoft To Do list found", str(ctx.exception))


# ---------------------------------------------------------------------------
# Plaid
# ---------------------------------------------------------------------------

class TestPlaid(unittest.TestCase):

    def _plaid_store(self, token: str = "plaid-tok") -> MagicMock:
        store = MagicMock()
        store.get_tokens.return_value = {"access_token": token}
        store.plaid_status.return_value = {"connected": True}
        return store

    def test_bootstrap_plaid_sandbox_stores_access_token(self) -> None:
        svc = _make_service()
        svc._store = MagicMock()

        def fake_post(url, data):
            if "public_token/create" in url:
                return {"public_token": "public-tok-123"}
            if "public_token/exchange" in url:
                return {"access_token": "access-tok-xyz"}
            return {}

        with patch("assistant_app.live_service.http_post", side_effect=fake_post):
            result = svc.bootstrap_plaid_sandbox("ins_chase")

        svc._store.set_tokens.assert_called_once()
        call_args = svc._store.set_tokens.call_args
        stored_tokens = call_args.args[1]
        self.assertEqual(stored_tokens["access_token"], "access-tok-xyz")
        self.assertEqual(result["institution_id"], "ins_chase")
        self.assertTrue(result["access_token_stored"])

    def test_bootstrap_plaid_raises_when_credentials_not_configured(self) -> None:
        svc = _make_service(config_overrides={"plaid_client_id": ""})
        with self.assertRaises(ValueError) as ctx:
            svc.bootstrap_plaid_sandbox("ins_chase")
        self.assertIn("Plaid credentials", str(ctx.exception))

    def test_list_plaid_accounts_returns_accounts(self) -> None:
        svc = _make_service()
        svc._store = self._plaid_store()
        raw_account = {
            "account_id": "acc-1",
            "name": "Checking",
            "type": "depository",
            "subtype": "checking",
            "balances": {"available": 1000.0, "current": 1050.0, "iso_currency_code": "USD"},
        }

        with patch("assistant_app.live_service.http_post", return_value={"accounts": [raw_account]}):
            result = svc.list_plaid_accounts()

        self.assertEqual(result["provider"], "plaid")
        self.assertEqual(len(result["accounts"]), 1)

    def test_list_plaid_accounts_raises_when_not_connected(self) -> None:
        svc = _make_service()
        svc._store.get_tokens.return_value = {}
        with self.assertRaises(ValueError) as ctx:
            svc.list_plaid_accounts()
        self.assertIn("Plaid is not connected", str(ctx.exception))

    def test_list_plaid_transactions_returns_transactions(self) -> None:
        svc = _make_service()
        svc._store = self._plaid_store()
        raw_response = {
            "transactions": [{"transaction_id": "txn-1", "amount": 12.50}],
            "total_transactions": 1,
        }

        with patch("assistant_app.live_service.http_post", return_value=raw_response):
            result = svc.list_plaid_transactions("2026-04-01", "2026-04-18")

        self.assertEqual(result["provider"], "plaid")
        self.assertEqual(result["total_transactions"], 1)

    def test_list_plaid_transactions_uses_defaults_when_dates_none(self) -> None:
        svc = _make_service()
        svc._store = self._plaid_store()

        with patch("assistant_app.live_service.http_post", return_value={"transactions": [], "total_transactions": 0}) as mock_post:
            svc.list_plaid_transactions(None, None)

        call_data = mock_post.call_args.args[1]
        self.assertIn("start_date", call_data)
        self.assertIn("end_date", call_data)

    def test_plaid_base_sandbox(self) -> None:
        svc = _make_service(config_overrides={"plaid_env": "sandbox"})
        self.assertIn("sandbox", svc._plaid_base())

    def test_plaid_base_production(self) -> None:
        svc = _make_service(config_overrides={"plaid_env": "production"})
        self.assertIn("production", svc._plaid_base())

    def test_plaid_base_development(self) -> None:
        svc = _make_service(config_overrides={"plaid_env": "development"})
        self.assertIn("development", svc._plaid_base())


# ---------------------------------------------------------------------------
# Live task update helpers
# ---------------------------------------------------------------------------

class TestLiveTaskUpdates(unittest.TestCase):

    def test_update_google_task_calls_http_patch(self) -> None:
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_patch", return_value={"status": "needsAction"}) as mock_patch:
            svc.update_google_task("list-1", "task-1", {"title": "updated title"})

        mock_patch.assert_called_once()
        url = mock_patch.call_args.args[0]
        self.assertIn("list-1", url)
        self.assertIn("task-1", url)

    def test_complete_google_task_sets_status_completed(self) -> None:
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_patch", return_value={"status": "completed"}) as mock_patch:
            svc.complete_google_task("list-1", "task-1")

        call_data = mock_patch.call_args.args[1]
        self.assertEqual(call_data["status"], "completed")

    def test_update_microsoft_task_calls_http_patch(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()

        with patch("assistant_app.live_service.http_patch", return_value={"status": "inProgress"}) as mock_patch:
            svc.update_microsoft_task("ms-list-1", "ms-task-1", {"title": "new title"})

        mock_patch.assert_called_once()
        url = mock_patch.call_args.args[0]
        self.assertIn("ms-list-1", url)
        self.assertIn("ms-task-1", url)

    def test_complete_microsoft_task_sets_status_completed(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()

        with patch("assistant_app.live_service.http_patch", return_value={"status": "completed"}) as mock_patch:
            svc.complete_microsoft_task("ms-list-1", "ms-task-1")

        call_data = mock_patch.call_args.args[1]
        self.assertEqual(call_data["status"], "completed")

    def test_create_microsoft_calendar_event_live_delegates(self) -> None:
        svc = _make_service()
        svc._store = _ms_store()
        raw_event = {
            "id": "ms-evt-live",
            "subject": "Live Event",
            "start": {"dateTime": "2026-04-22T09:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-04-22T10:00:00", "timeZone": "UTC"},
        }

        with patch("assistant_app.live_service.http_post", return_value=raw_event):
            result = svc.create_microsoft_calendar_event_live(raw_event)

        self.assertIn("event", result)


# ---------------------------------------------------------------------------
# get_drive_documents_for_event
# ---------------------------------------------------------------------------

class TestGetDriveDocumentsForEvent(unittest.TestCase):

    def test_returns_document_references_on_success(self) -> None:
        svc = _make_service()
        svc._store = _google_store()
        raw_doc = {
            "id": "doc-1",
            "name": "Architecture Review Deck",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/doc-1",
        }

        with patch("assistant_app.live_service.http_get", return_value={"files": [raw_doc]}):
            refs = svc.get_drive_documents_for_event("Architecture Review")

        self.assertEqual(len(refs), 1)

    def test_returns_empty_list_when_http_request_error(self) -> None:
        from assistant_app.http_client import HttpRequestError
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_get", side_effect=HttpRequestError("403 Forbidden", 403)):
            refs = svc.get_drive_documents_for_event("Some Meeting")

        self.assertEqual(refs, [])

    def test_returns_empty_list_when_value_error(self) -> None:
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_get", side_effect=ValueError("Not connected")):
            refs = svc.get_drive_documents_for_event("Some Meeting")

        self.assertEqual(refs, [])

    def test_strips_single_quotes_from_event_title(self) -> None:
        """Event title with single quotes must not break the Drive query."""
        svc = _make_service()
        svc._store = _google_store()

        with patch("assistant_app.live_service.http_get", return_value={"files": []}) as mock_get:
            svc.get_drive_documents_for_event("O'Brien's Standup")

        url = mock_get.call_args.args[0]
        # The apostrophe should be stripped so the query doesn't break
        self.assertNotIn("'O'Brien", url)


if __name__ == "__main__":
    unittest.main()
