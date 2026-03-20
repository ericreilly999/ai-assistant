from __future__ import annotations

import base64
import json
from typing import Any

from assistant_app.config import AppConfig
from assistant_app.orchestrator import AssistantOrchestrator
from assistant_app.registry import ProviderRegistry
from assistant_app.response import json_response


def build_handler(config: AppConfig | None = None, registry: ProviderRegistry | None = None):
    active_config = config or AppConfig.from_env()
    active_registry = registry or ProviderRegistry(mock_mode=active_config.mock_provider_mode)
    orchestrator = AssistantOrchestrator(active_config, active_registry)

    def _handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
        method = _resolve_method(event)
        path = _resolve_path(event)

        if method == "OPTIONS":
            return json_response(200, {"ok": True})

        if method == "GET" and path == "/health":
            return json_response(
                200,
                {
                    "service": "ai-assistant",
                    "environment": active_config.app_env,
                    "mock_provider_mode": active_config.mock_provider_mode,
                    "providers": active_registry.providers(),
                },
            )

        if method == "GET" and path == "/v1/integrations":
            return json_response(200, {"integrations": active_registry.integration_status()})

        if method == "POST" and path == "/v1/chat/plan":
            body = _load_json_body(event)
            return json_response(200, orchestrator.plan(body).to_dict())

        if method == "POST" and path == "/v1/chat/execute":
            body = _load_json_body(event)
            try:
                result = orchestrator.execute(body)
                return json_response(200, result.to_dict())
            except ValueError as exc:
                return json_response(400, {"message": str(exc)})

        return json_response(404, {"message": f"No route for {method} {path}"})

    return _handler


def _resolve_method(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    return event.get("httpMethod") or http_context.get("method") or "GET"


def _resolve_path(event: dict[str, Any]) -> str:
    return event.get("rawPath") or event.get("path") or "/"


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


lambda_handler = build_handler()