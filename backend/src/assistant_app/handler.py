from __future__ import annotations

import base64
import html
import json
import logging
import re
from typing import Any
from urllib.parse import parse_qsl

from assistant_app.config import AppConfig
from assistant_app.http_client import HttpRequestError
from assistant_app.live_service import LocalIntegrationService
from assistant_app.orchestrator import AssistantOrchestrator
from assistant_app.registry import ProviderRegistry
from assistant_app.response import html_response, json_response, redirect_response

logger = logging.getLogger(__name__)


def _redact_body(body: str) -> str:
    """Redact OAuth token values and Plaid secrets from provider response bodies before logging."""
    if not body:
        return body
    # Redact JSON fields whose values look like tokens/secrets
    return re.sub(
        r'("(?:access_token|refresh_token|id_token|token|secret|plaid_secret|client_secret)"\s*:\s*")([\w\-\._~]+)(")',
        r'\1[REDACTED]\3',
        body
    )


def _extract_user_id(event: dict[str, Any]) -> str:
    """Extract the Cognito ``sub`` claim from the API Gateway v2 JWT authorizer context.

    API Gateway v2 JWT authorizer populates:
        event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]

    Falls back to ``"local"`` when the authorizer context is absent (local
    development, unit tests, or unauthenticated routes such as /health).
    """
    try:
        sub = (
            (event.get("requestContext") or {})
            .get("authorizer", {})
            .get("jwt", {})
            .get("claims", {})
            .get("sub")
        )
        if sub:
            return sub
        logger.warning(
            "user_id not found in JWT claims, falling back to local — check API Gateway authorizer config"
        )
        return "local"
    except (AttributeError, TypeError):
        logger.warning(
            "user_id not found in JWT claims, falling back to local — check API Gateway authorizer config"
        )
        return "local"


def build_handler(
    config: AppConfig | None = None,
    registry: ProviderRegistry | None = None,
    live_service: LocalIntegrationService | None = None,
):
    active_config = config or AppConfig.from_env()
    active_registry = registry or ProviderRegistry(mock_mode=active_config.mock_provider_mode)

    def _handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
        method = _resolve_method(event)
        path = _resolve_path(event)
        query = _resolve_query_params(event)

        # Resolve per-request live service scoped to the authenticated user.
        # When a live_service override is provided (tests / local dev), use it
        # directly.  Otherwise build a fresh instance carrying the Cognito sub.
        if live_service is not None:
            dev_service = live_service
        else:
            user_id = _extract_user_id(event)
            dev_service = LocalIntegrationService(active_config, active_registry, user_id=user_id)

        # Build the orchestrator per-request so it always uses the user-scoped
        # live_service.  Building it once at module load would default to
        # user_id="local" for every request regardless of the authenticated user.
        orchestrator = AssistantOrchestrator(active_config, active_registry, dev_service)

        if method == "OPTIONS":
            return json_response(200, {"ok": True})

        try:
            if method == "GET" and path == "/health":
                return json_response(
                    200,
                    {
                        "service": "ai-assistant",
                        "environment": active_config.app_env,
                        "mock_provider_mode": active_config.mock_provider_mode,
                        "providers": active_registry.providers(),
                        "local_env_file": active_config.local_env_file,
                        "provider_secret_status": active_config.provider_secret_status,
                        "local_store_file": active_config.local_store_file,
                    },
                )

            if method == "GET" and path == "/v1/integrations":
                return json_response(
                    200,
                    {
                        "integrations": active_registry.integration_status(
                            provider_secret_status=active_config.provider_secret_status,
                            secret_source="local_env_file" if active_config.local_env_file else "environment",
                        )
                    },
                )

            if method == "GET" and path == "/v1/dev/connections":
                return json_response(200, dev_service.connection_status())

            if method == "GET" and path == "/oauth/google/start":
                try:
                    return redirect_response(dev_service.google_auth_url())
                except ValueError as exc:
                    return html_response(400, _oauth_not_configured_page("Google", str(exc)))

            if method == "GET" and path == "/oauth/google/callback":
                result = dev_service.complete_google_auth(query.get("code", ""), query.get("state", ""))
                return html_response(200, _oauth_callback_page("Google", result))

            if method == "GET" and path == "/oauth/microsoft/start":
                try:
                    return redirect_response(dev_service.microsoft_auth_url())
                except ValueError as exc:
                    return html_response(400, _oauth_not_configured_page("Microsoft", str(exc)))

            if method == "GET" and path == "/oauth/microsoft/callback":
                result = dev_service.complete_microsoft_auth(query.get("code", ""), query.get("state", ""))
                return html_response(200, _oauth_callback_page("Microsoft", result))

            if method == "GET" and path == "/v1/dev/google/calendar/events":
                if not query.get("start") or not query.get("end"):
                    return json_response(400, {"error": "start and end query parameters are required"})
                return json_response(200, dev_service.list_google_calendar_events(query.get("start"), query.get("end")))

            if method == "POST" and path == "/v1/dev/google/calendar/events":
                return json_response(200, dev_service.create_google_calendar_event(_load_json_body(event)))

            if method == "GET" and path == "/v1/dev/google/tasks/lists":
                return json_response(200, dev_service.list_google_tasklists())

            if method == "GET" and path == "/v1/dev/google/tasks/items":
                return json_response(200, dev_service.list_google_tasks(query.get("list_id"), query.get("list_name")))

            if method == "POST" and path == "/v1/dev/google/tasks/grocery-items":
                return json_response(200, dev_service.add_google_grocery_items(_load_json_body(event)))

            if method == "GET" and path == "/v1/dev/google/drive/documents":
                return json_response(200, dev_service.list_google_drive_documents(query.get("q")))

            if method == "GET" and path == "/v1/dev/google/drive/export":
                file_id = query.get("file_id", "")
                mime_type = query.get("mime_type", "text/plain")
                return json_response(200, dev_service.export_google_drive_document(file_id, mime_type))

            if method == "GET" and path == "/v1/dev/microsoft/calendar/events":
                if not query.get("start") or not query.get("end"):
                    return json_response(400, {"error": "start and end query parameters are required"})
                return json_response(200, dev_service.list_microsoft_calendar_events(query.get("start"), query.get("end")))

            if method == "POST" and path == "/v1/dev/microsoft/calendar/events":
                return json_response(200, dev_service.create_microsoft_calendar_event(_load_json_body(event)))

            if method == "GET" and path == "/v1/dev/microsoft/todo/lists":
                return json_response(200, dev_service.list_microsoft_tasklists())

            if method == "GET" and path == "/v1/dev/microsoft/todo/items":
                return json_response(200, dev_service.list_microsoft_tasks(query.get("list_id"), query.get("list_name")))

            if method == "POST" and path == "/v1/dev/microsoft/todo/grocery-items":
                return json_response(200, dev_service.add_microsoft_grocery_items(_load_json_body(event)))

            if method == "POST" and path == "/v1/dev/plaid/sandbox/bootstrap":
                body = _load_json_body(event)
                institution_id = body.get("institution_id", "ins_109508")
                return json_response(200, dev_service.bootstrap_plaid_sandbox(institution_id))

            if method == "GET" and path == "/v1/dev/plaid/accounts":
                return json_response(200, dev_service.list_plaid_accounts())

            if method == "GET" and path == "/v1/dev/plaid/transactions":
                if not query.get("start_date") or not query.get("end_date"):
                    return json_response(400, {"error": "start_date and end_date query parameters are required"})
                return json_response(200, dev_service.list_plaid_transactions(query.get("start_date"), query.get("end_date")))

            if method == "POST" and path == "/v1/chat/plan":
                body = _load_json_body(event)
                return json_response(200, orchestrator.plan(body).to_dict())

            if method == "POST" and path == "/v1/chat/execute":
                body = _load_json_body(event)
                exec_result = orchestrator.execute(body)
                return json_response(200, exec_result.to_dict())
        except ValueError as exc:
            return json_response(400, {"message": str(exc)})
        except HttpRequestError as exc:
            logger.error(
                "Provider request failed: %s %s — body: %s",
                exc.status_code,
                getattr(exc, "url", ""),
                _redact_body(exc.body or ""),
            )
            return json_response(
                exc.status_code or 502,
                {"message": "Provider request failed. Please try again."},
            )

        return json_response(404, {"message": f"No route for {method} {path}"})

    return _handler


def _resolve_method(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    return event.get("httpMethod") or http_context.get("method") or "GET"


def _resolve_path(event: dict[str, Any]) -> str:
    # For stage-based URLs (e.g. https://id.execute-api.region.amazonaws.com/dev/health)
    # AWS includes the stage prefix in rawPath. Strip it using requestContext.stage.
    # The $default stage has no prefix. Custom domain URLs also have no prefix.
    raw_path: str = event.get("rawPath") or event.get("path") or "/"
    request_context = event.get("requestContext") or {}
    stage: str = request_context.get("stage", "")
    if stage and stage != "$default" and raw_path.startswith(f"/{stage}/"):
        return raw_path[len(f"/{stage}"):]
    if stage and stage != "$default" and raw_path == f"/{stage}":
        return "/"
    return raw_path


def _resolve_query_params(event: dict[str, Any]) -> dict[str, str]:
    direct = event.get("queryStringParameters")
    if isinstance(direct, dict):
        return {str(key): str(value) for key, value in direct.items() if value is not None}

    raw_query = event.get("rawQueryString")
    if raw_query:
        return dict(parse_qsl(raw_query, keep_blank_values=True))
    return {}


def _load_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, dict):
        return body
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if not body:
        return {}
    return json.loads(body)


def _oauth_not_configured_page(provider_name: str, message: str) -> str:
    return (
        "<html><body style=\"font-family: sans-serif; padding: 24px;\">"
        f"<h1>{provider_name} Not Configured</h1>"
        f"<p style=\"color: #c00;\">{message}</p>"
        "<p>Add the required credentials to <code>backend/.env.local</code> "
        "and restart the local server, then try again.</p>"
        "<p>See <code>backend/.env.local.example</code> for the required variable names.</p>"
        "</body></html>"
    )


def _oauth_callback_page(provider_name: str, result: dict[str, Any]) -> str:
    escaped = html.escape(json.dumps(result, indent=2))
    return (
        "<html><body style=\"font-family: sans-serif; padding: 24px;\">"
        f"<h1>{html.escape(provider_name)} Connected</h1>"
        "<p>The local dev integration is now authorized. You may close this window.</p>"
        f"<pre>{escaped}</pre>"
        "<p>You can continue with local smoke validation.</p>"
        "</body></html>"
    )



lambda_handler = build_handler()
