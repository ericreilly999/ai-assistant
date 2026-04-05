from __future__ import annotations

import secrets
import urllib.parse
from datetime import UTC, datetime
from typing import Any

from assistant_app.config import AppConfig
from assistant_app.dev_store import DevTokenStore
from assistant_app.http_client import (
    HttpRequestError,
    http_get,
    http_get_text,
    http_patch,
    http_post,
    http_post_form,
)
from assistant_app.models import DocumentReference
from assistant_app.registry import ProviderRegistry

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
_GOOGLE_TASKS_BASE = "https://tasks.googleapis.com/tasks/v1"
_GOOGLE_DRIVE_BASE = "https://www.googleapis.com/drive/v3"

_GOOGLE_SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/drive.readonly",
])

_MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_MS_GRAPH_BASE = "https://graph.microsoft.com/v1.0"

_MS_SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "offline_access",
    "Calendars.ReadWrite",
    "Tasks.ReadWrite",
    "Files.Read",
])


class LocalIntegrationService:
    """Handles OAuth flows and live provider API calls during local development."""

    def __init__(self, config: AppConfig, registry: ProviderRegistry) -> None:
        self.config = config
        self.registry = registry
        self._store = DevTokenStore(config.local_store_file)

    # -------------------------------------------------------------------------
    # Connection status
    # -------------------------------------------------------------------------

    def connection_status(self) -> dict[str, Any]:
        google_tokens = self._store.get_tokens("google")
        ms_tokens = self._store.get_tokens("microsoft")
        plaid_info = self._store.plaid_status()
        return {
            "google": {
                "connected": bool(google_tokens and google_tokens.get("access_token")),
                "expires_at": self._store.expires_at("google"),
            },
            "microsoft": {
                "connected": bool(ms_tokens and ms_tokens.get("access_token")),
                "expires_at": self._store.expires_at("microsoft"),
            },
            "plaid": plaid_info,
        }

    # -------------------------------------------------------------------------
    # Google OAuth
    # -------------------------------------------------------------------------

    def google_auth_url(self) -> str:
        if not self.config.google_client_id:
            raise ValueError("GOOGLE_CLIENT_ID is not configured.")
        state = secrets.token_urlsafe(16)
        self._store.merge_tokens("google_oauth_state", {"state": state})
        params = {
            "client_id": self.config.google_client_id,
            "redirect_uri": self.config.google_redirect_uri,
            "response_type": "code",
            "scope": _GOOGLE_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{_GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def complete_google_auth(self, code: str, state: str) -> dict[str, Any]:
        if not self.config.google_client_id or not self.config.google_client_secret:
            raise ValueError("Google OAuth credentials are not configured.")
        tokens = http_post_form(
            _GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": self.config.google_client_id,
                "client_secret": self.config.google_client_secret,
                "redirect_uri": self.config.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        tokens["stored_at"] = datetime.now(UTC).isoformat()
        self._store.set_tokens("google", tokens)
        return {"provider": "google", "stored": True, "scope": tokens.get("scope", "")}

    def _google_token(self) -> str:
        tokens = self._store.get_tokens("google") or {}
        access_token = tokens.get("access_token", "")
        if not access_token:
            raise ValueError("Google is not connected. Run the OAuth flow first.")
        return access_token

    def _google_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._google_token()}"}

    # -------------------------------------------------------------------------
    # Microsoft OAuth
    # -------------------------------------------------------------------------

    def microsoft_auth_url(self) -> str:
        if not self.config.microsoft_client_id:
            raise ValueError("MICROSOFT_CLIENT_ID is not configured.")
        state = secrets.token_urlsafe(16)
        self._store.merge_tokens("microsoft_oauth_state", {"state": state})
        params = {
            "client_id": self.config.microsoft_client_id,
            "redirect_uri": self.config.microsoft_redirect_uri,
            "response_type": "code",
            "scope": _MS_SCOPES,
            "response_mode": "query",
            "state": state,
        }
        return f"{_MS_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def complete_microsoft_auth(self, code: str, state: str) -> dict[str, Any]:
        if not self.config.microsoft_client_id or not self.config.microsoft_client_secret:
            raise ValueError("Microsoft OAuth credentials are not configured.")
        tokens = http_post_form(
            _MS_TOKEN_URL,
            {
                "code": code,
                "client_id": self.config.microsoft_client_id,
                "client_secret": self.config.microsoft_client_secret,
                "redirect_uri": self.config.microsoft_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        tokens["stored_at"] = datetime.now(UTC).isoformat()
        self._store.set_tokens("microsoft", tokens)
        return {"provider": "microsoft", "stored": True, "scope": tokens.get("scope", "")}

    def _ms_token(self) -> str:
        tokens = self._store.get_tokens("microsoft") or {}
        access_token = tokens.get("access_token", "")
        if not access_token:
            raise ValueError("Microsoft is not connected. Run the OAuth flow first.")
        return access_token

    def _ms_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._ms_token()}"}

    # -------------------------------------------------------------------------
    # Google Calendar
    # -------------------------------------------------------------------------

    def list_google_calendar_events(self, start: str | None, end: str | None) -> dict[str, Any]:
        adapter = self.registry.get("google_calendar")
        params: dict[str, str] = {"singleEvents": "true", "orderBy": "startTime", "maxResults": "50"}
        if start:
            params["timeMin"] = start
        if end:
            params["timeMax"] = end
        url = f"{_GOOGLE_CALENDAR_BASE}/calendars/primary/events?{urllib.parse.urlencode(params)}"
        raw = http_get(url, self._google_headers())
        events = [adapter.normalize_event(item).to_dict() for item in raw.get("items", [])]
        return {"events": events, "provider": "google_calendar"}

    def create_google_calendar_event(self, body: dict[str, Any]) -> dict[str, Any]:
        adapter = self.registry.get("google_calendar")
        url = f"{_GOOGLE_CALENDAR_BASE}/calendars/primary/events"
        raw = http_post(url, body, self._google_headers())
        return {"event": adapter.normalize_event(raw).to_dict(), "provider": "google_calendar"}

    # -------------------------------------------------------------------------
    # Google Tasks
    # -------------------------------------------------------------------------

    def list_google_tasklists(self) -> dict[str, Any]:
        url = f"{_GOOGLE_TASKS_BASE}/users/@me/lists"
        raw = http_get(url, self._google_headers())
        lists = [{"id": item["id"], "title": item.get("title", "")} for item in raw.get("items", [])]
        return {"task_lists": lists, "provider": "google_tasks"}

    def list_google_tasks(self, list_id: str | None, list_name: str | None) -> dict[str, Any]:
        adapter = self.registry.get("google_tasks")
        resolved_id = list_id or self._resolve_google_tasklist_id(list_name)
        url = f"{_GOOGLE_TASKS_BASE}/lists/{resolved_id}/tasks?showCompleted=true&maxResults=100"
        raw = http_get(url, self._google_headers())
        tasks = [adapter.normalize_task({**item, "list_name": list_name or resolved_id}).to_dict()
                 for item in raw.get("items", [])]
        return {"tasks": tasks, "provider": "google_tasks"}

    def add_google_grocery_items(self, body: dict[str, Any]) -> dict[str, Any]:
        list_name = body.get("list_name", "Groceries")
        items: list[str] = body.get("items", [])
        list_id = self._resolve_google_tasklist_id(list_name)
        created = []
        for item in items:
            url = f"{_GOOGLE_TASKS_BASE}/lists/{list_id}/tasks"
            result = http_post(url, {"title": item}, self._google_headers())
            created.append(result.get("id"))
        return {"created_count": len(created), "list_name": list_name, "provider": "google_tasks"}

    def _resolve_google_tasklist_id(self, list_name: str | None) -> str:
        raw = http_get(f"{_GOOGLE_TASKS_BASE}/users/@me/lists", self._google_headers())
        for item in raw.get("items", []):
            if list_name and item.get("title", "").lower() == list_name.lower():
                return item["id"]
        for item in raw.get("items", []):
            return item["id"]
        raise ValueError(f"No task list found matching '{list_name}'.")

    # -------------------------------------------------------------------------
    # Google Drive
    # -------------------------------------------------------------------------

    def list_google_drive_documents(self, q: str | None) -> dict[str, Any]:
        adapter = self.registry.get("google_drive")
        query = q or "mimeType='application/vnd.google-apps.document'"
        params = {
            "q": query,
            "fields": "files(id,name,mimeType,webViewLink)",
            "pageSize": "20",
        }
        url = f"{_GOOGLE_DRIVE_BASE}/files?{urllib.parse.urlencode(params)}"
        raw = http_get(url, self._google_headers())
        docs = [adapter.normalize_file(item).to_dict() for item in raw.get("files", [])]
        return {"documents": docs, "provider": "google_drive"}

    def export_google_drive_document(self, file_id: str, mime_type: str) -> dict[str, Any]:
        params = {"mimeType": mime_type}
        url = f"{_GOOGLE_DRIVE_BASE}/files/{file_id}/export?{urllib.parse.urlencode(params)}"
        content = http_get_text(url, self._google_headers())
        return {"file_id": file_id, "mime_type": mime_type, "content": content[:4000]}

    # -------------------------------------------------------------------------
    # Microsoft Calendar
    # -------------------------------------------------------------------------

    def list_microsoft_calendar_events(self, start: str | None, end: str | None) -> dict[str, Any]:
        adapter = self.registry.get("microsoft_calendar")
        params: dict[str, str] = {"$top": "50", "$orderby": "start/dateTime"}
        if start:
            params["startDateTime"] = start
        if end:
            params["endDateTime"] = end
        url = f"{_MS_GRAPH_BASE}/me/calendarView?{urllib.parse.urlencode(params)}"
        raw = http_get(url, self._ms_headers())
        events = [adapter.normalize_event(item).to_dict() for item in raw.get("value", [])]
        return {"events": events, "provider": "microsoft_calendar"}

    def create_microsoft_calendar_event(self, body: dict[str, Any]) -> dict[str, Any]:
        adapter = self.registry.get("microsoft_calendar")
        url = f"{_MS_GRAPH_BASE}/me/events"
        raw = http_post(url, body, self._ms_headers())
        return {"event": adapter.normalize_event(raw).to_dict(), "provider": "microsoft_calendar"}

    # -------------------------------------------------------------------------
    # Microsoft To Do
    # -------------------------------------------------------------------------

    def list_microsoft_tasklists(self) -> dict[str, Any]:
        url = f"{_MS_GRAPH_BASE}/me/todo/lists"
        raw = http_get(url, self._ms_headers())
        lists = [{"id": item["id"], "displayName": item.get("displayName", "")} for item in raw.get("value", [])]
        return {"task_lists": lists, "provider": "microsoft_todo"}

    def list_microsoft_tasks(self, list_id: str | None, list_name: str | None) -> dict[str, Any]:
        adapter = self.registry.get("microsoft_todo")
        resolved_id = list_id or self._resolve_ms_tasklist_id(list_name)
        url = f"{_MS_GRAPH_BASE}/me/todo/lists/{resolved_id}/tasks?$top=100"
        raw = http_get(url, self._ms_headers())
        tasks = [adapter.normalize_task({**item, "list_name": list_name or resolved_id}).to_dict()
                 for item in raw.get("value", [])]
        return {"tasks": tasks, "provider": "microsoft_todo"}

    def add_microsoft_grocery_items(self, body: dict[str, Any]) -> dict[str, Any]:
        list_name = body.get("list_name", "Groceries")
        items: list[str] = body.get("items", [])
        list_id = self._resolve_ms_tasklist_id(list_name)
        created = []
        for item in items:
            url = f"{_MS_GRAPH_BASE}/me/todo/lists/{list_id}/tasks"
            result = http_post(url, {"title": item}, self._ms_headers())
            created.append(result.get("id"))
        return {"created_count": len(created), "list_name": list_name, "provider": "microsoft_todo"}

    def _resolve_ms_tasklist_id(self, list_name: str | None) -> str:
        raw = http_get(f"{_MS_GRAPH_BASE}/me/todo/lists", self._ms_headers())
        for item in raw.get("value", []):
            if list_name and item.get("displayName", "").lower() == list_name.lower():
                return item["id"]
        for item in raw.get("value", []):
            return item["id"]
        raise ValueError(f"No Microsoft To Do list found matching '{list_name}'.")

    # -------------------------------------------------------------------------
    # Plaid
    # -------------------------------------------------------------------------

    def bootstrap_plaid_sandbox(self, institution_id: str) -> dict[str, Any]:
        if not self.config.plaid_client_id or not self.config.plaid_secret:
            raise ValueError("Plaid credentials (PLAID_CLIENT_ID, PLAID_SECRET) are not configured.")
        base = self._plaid_base()
        token_response = http_post(
            f"{base}/sandbox/public_token/create",
            {
                "client_id": self.config.plaid_client_id,
                "secret": self.config.plaid_secret,
                "institution_id": institution_id,
                "initial_products": ["transactions"],
            },
        )
        public_token = token_response["public_token"]
        exchange_response = http_post(
            f"{base}/item/public_token/exchange",
            {
                "client_id": self.config.plaid_client_id,
                "secret": self.config.plaid_secret,
                "public_token": public_token,
            },
        )
        access_token = exchange_response["access_token"]
        self._store.set_tokens("plaid", {
            "access_token": access_token,
            "institution_id": institution_id,
            "stored_at": datetime.now(UTC).isoformat(),
        })
        return {"institution_id": institution_id, "access_token_stored": True}

    def list_plaid_accounts(self) -> dict[str, Any]:
        adapter = self.registry.get("plaid")
        access_token = self._plaid_access_token()
        base = self._plaid_base()
        raw = http_post(
            f"{base}/accounts/get",
            {
                "client_id": self.config.plaid_client_id,
                "secret": self.config.plaid_secret,
                "access_token": access_token,
            },
        )
        accounts = [adapter.normalize_account(item).to_dict() for item in raw.get("accounts", [])]
        return {"accounts": accounts, "provider": "plaid"}

    def list_plaid_transactions(self, start_date: str | None, end_date: str | None) -> dict[str, Any]:
        access_token = self._plaid_access_token()
        base = self._plaid_base()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        thirty_days_ago = datetime.now(UTC).replace(day=1).strftime("%Y-%m-%d")
        raw = http_post(
            f"{base}/transactions/get",
            {
                "client_id": self.config.plaid_client_id,
                "secret": self.config.plaid_secret,
                "access_token": access_token,
                "start_date": start_date or thirty_days_ago,
                "end_date": end_date or today,
            },
        )
        return {
            "transactions": raw.get("transactions", []),
            "total_transactions": raw.get("total_transactions", 0),
            "provider": "plaid",
        }

    def _plaid_access_token(self) -> str:
        tokens = self._store.get_tokens("plaid") or {}
        access_token = tokens.get("access_token", "")
        if not access_token:
            raise ValueError("Plaid is not connected. Run the sandbox bootstrap first.")
        return access_token

    def _plaid_base(self) -> str:
        env = self.config.plaid_env
        if env == "production":
            return "https://production.plaid.com"
        if env == "development":
            return "https://development.plaid.com"
        return "https://sandbox.plaid.com"

    # -------------------------------------------------------------------------
    # Live task updates (used by _execute_live in orchestrator)
    # -------------------------------------------------------------------------

    def update_google_task(self, list_id: str, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        url = f"{_GOOGLE_TASKS_BASE}/lists/{list_id}/tasks/{task_id}"
        return http_patch(url, updates, self._google_headers())

    def complete_google_task(self, list_id: str, task_id: str) -> dict[str, Any]:
        return self.update_google_task(list_id, task_id, {"status": "completed", "hidden": True})

    def update_microsoft_task(self, list_id: str, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        url = f"{_MS_GRAPH_BASE}/me/todo/lists/{list_id}/tasks/{task_id}"
        return http_patch(url, updates, self._ms_headers())

    def complete_microsoft_task(self, list_id: str, task_id: str) -> dict[str, Any]:
        return self.update_microsoft_task(list_id, task_id, {"status": "completed"})

    def create_microsoft_calendar_event_live(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.create_microsoft_calendar_event(payload)

    def get_drive_documents_for_event(self, event_title: str) -> list[DocumentReference]:
        """Fetch Drive documents likely related to a calendar event by title keyword search."""
        try:
            q = f"name contains '{event_title.replace(chr(39), '')}' and mimeType='application/vnd.google-apps.document'"
            result = self.list_google_drive_documents(q)
            adapter = self.registry.get("google_drive")
            return [adapter.normalize_file(doc) for doc in result.get("documents", [])]
        except (HttpRequestError, ValueError):
            return []
