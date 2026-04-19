"""Handler tests — updated for Phase 13 agent loop.

plan() tests now inject MockBedrockAgent via patching. execute() tests are unchanged.
Intent values updated: domain-specific → 'agent'.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from assistant_app.bedrock_client import MockBedrockAgent
from assistant_app.config import AppConfig
from assistant_app.consent import payload_hash
from assistant_app.handler import build_handler
from assistant_app.registry import ProviderRegistry


def _make_config(**overrides):
    defaults = {
        "app_env": "dev",
        "log_level": "INFO",
        "mock_provider_mode": True,
        "proposal_ttl_minutes": 15,
        "default_timezone": "America/New_York",
        "bedrock_router_model_id": "mock-router",
        "bedrock_guardrail_id": "mock-guardrail",
        "bedrock_guardrail_version": "DRAFT",
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


def _tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tu-001") -> dict:
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": tool_use_id,
                            "name": tool_name,
                            "input": tool_input,
                        }
                    }
                ],
            }
        },
        "usage": {"inputTokens": 100, "outputTokens": 50},
    }


def _text_response(text: str) -> dict:
    return {
        "stopReason": "end_turn",
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "usage": {"inputTokens": 80, "outputTokens": 40},
    }


class HandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = _make_config()
        self.registry = ProviderRegistry(mock_mode=True)
        self.handler = build_handler(self.config, self.registry)

    def _req(self, method: str, path: str, body: dict | None = None, query: dict | None = None) -> dict:
        event: dict = {
            "rawPath": path,
            "requestContext": {"http": {"method": method}},
        }
        if body is not None:
            event["body"] = json.dumps(body)
        if query:
            event["queryStringParameters"] = query
        return event

    def _plan_with_mock(self, message: str, mock_turns: list[dict], providers=None) -> dict:
        """Helper: call /v1/chat/plan with MockBedrockAgent injected."""
        from assistant_app.orchestrator import AssistantOrchestrator

        orch = AssistantOrchestrator(self.config, self.registry)
        orch._router = MockBedrockAgent(mock_turns)

        with patch(
            "assistant_app.handler.AssistantOrchestrator",
            return_value=orch,
        ):
            handler = build_handler(self.config, self.registry)
            body: dict = {"message": message}
            if providers:
                body["providers"] = providers
            response = handler(self._req("POST", "/v1/chat/plan", body), None)
        return json.loads(response["body"])

    # ------------------------------------------------------------------
    # Infrastructure routes
    # ------------------------------------------------------------------

    def test_health_route(self) -> None:
        response = self.handler(self._req("GET", "/health"), None)
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["environment"], "dev")
        self.assertTrue(body["mock_provider_mode"])

    def test_health_includes_provider_list(self) -> None:
        response = self.handler(self._req("GET", "/health"), None)
        body = json.loads(response["body"])
        self.assertIn("providers", body)
        self.assertIsInstance(body["providers"], list)
        self.assertGreater(len(body["providers"]), 0)

    def test_options_returns_200(self) -> None:
        response = self.handler(self._req("OPTIONS", "/v1/chat/plan"), None)
        self.assertEqual(response["statusCode"], 200)

    def test_404_for_unknown_route(self) -> None:
        response = self.handler(self._req("GET", "/does-not-exist"), None)
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 404)
        self.assertIn("No route", body["message"])

    def test_health_with_stage_prefix_stripped(self) -> None:
        event = {
            "rawPath": "/dev/health",
            "requestContext": {"http": {"method": "GET"}, "stage": "dev"},
        }
        response = self.handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["environment"], "dev")

    def test_integrations_route(self) -> None:
        response = self.handler(self._req("GET", "/v1/integrations"), None)
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("integrations", body)
        self.assertIsInstance(body["integrations"], list)

    # ------------------------------------------------------------------
    # OAuth routes
    # ------------------------------------------------------------------

    def test_google_oauth_start_redirects_when_not_configured(self) -> None:
        response = self.handler(self._req("GET", "/oauth/google/start"), None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Not Configured", response["body"])

    def test_microsoft_oauth_start_redirects_when_not_configured(self) -> None:
        response = self.handler(self._req("GET", "/oauth/microsoft/start"), None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Not Configured", response["body"])

    # ------------------------------------------------------------------
    # Plan routes — Phase 13: inject MockBedrockAgent, expect intent='agent'
    # ------------------------------------------------------------------

    def test_plan_route_grocery(self) -> None:
        body = self._plan_with_mock(
            "Add bananas to my grocery list",
            [
                _tool_use_response("get_grocery_lists", {}, tool_use_id="tu-gl"),
                _tool_use_response(
                    "propose_grocery_items",
                    {"list_name": "Groceries", "items": ["bananas"]},
                    tool_use_id="tu-gi",
                ),
                _text_response("Proposed adding bananas to your Groceries list."),
            ],
        )
        self.assertEqual(body["intent"], "agent")
        self.assertGreaterEqual(len(body["proposals"]), 1)

    def test_plan_route_calendar(self) -> None:
        body = self._plan_with_mock(
            "What does my day look like tomorrow?",
            [
                _tool_use_response(
                    "get_calendar_events",
                    {"start": "2026-04-19T00:00:00-04:00", "end": "2026-04-19T23:59:59-04:00"},
                ),
                _text_response(
                    "Tomorrow you have Team Standup at 9am and Architecture Review at 2pm."
                ),
            ],
        )
        self.assertEqual(body["intent"], "agent")
        self.assertIn("Tomorrow", body["message"])

    def test_plan_route_meeting_prep(self) -> None:
        body = self._plan_with_mock(
            "Prepare me for my architecture review",
            [
                _tool_use_response("get_meeting_documents", {"keyword": "architecture review"}),
                _text_response("For your review I found Architecture Review Deck in Drive."),
            ],
        )
        self.assertEqual(body["intent"], "agent")

    def test_plan_route_tasks_intent(self) -> None:
        body = self._plan_with_mock(
            "Complete my task",
            [
                _tool_use_response("get_task_lists", {}, tool_use_id="tu-tl"),
                _tool_use_response("get_tasks", {"list_id": "list-001"}, tool_use_id="tu-gt"),
                _tool_use_response(
                    "propose_task_complete",
                    {"list_id": "list-001", "task_id": "task-001"},
                    tool_use_id="tu-tc",
                ),
                _text_response("Proposed completing your task."),
            ],
        )
        self.assertEqual(body["intent"], "agent")

    def test_plan_route_general_fallback_returns_helpful_message(self) -> None:
        body = self._plan_with_mock(
            "something completely unrecognized xyz",
            [
                _text_response(
                    "I can help you with calendars, tasks, grocery lists, and meeting prep."
                ),
            ],
        )
        self.assertEqual(body["intent"], "agent")
        self.assertIn("calendars", body["message"])

    def test_plan_route_warnings_present_in_mock_mode(self) -> None:
        body = self._plan_with_mock(
            "What does my day look like tomorrow?",
            [
                _tool_use_response(
                    "get_calendar_events",
                    {"start": "2026-04-19T00:00:00-04:00", "end": "2026-04-19T23:59:59-04:00"},
                ),
                _text_response("Tomorrow you have meetings."),
            ],
        )
        self.assertGreater(len(body["warnings"]), 0)

    # ------------------------------------------------------------------
    # Execute routes
    # ------------------------------------------------------------------

    def test_execute_route_happy_path(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk", "eggs"]}
        response = self.handler(
            self._req(
                "POST",
                "/v1/chat/execute",
                {
                    "approved": True,
                    "provider": "google_tasks",
                    "action_type": "upsert_grocery_items",
                    "payload": payload,
                    "payload_hash": payload_hash(payload),
                },
            ),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("mock", body["message"])

    def test_execute_route_rejects_invalid_hash(self) -> None:
        response = self.handler(
            self._req(
                "POST",
                "/v1/chat/execute",
                {
                    "approved": True,
                    "provider": "google_tasks",
                    "action_type": "upsert_grocery_items",
                    "payload": {"items": ["milk"]},
                    "payload_hash": "bad-hash",
                },
            ),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Payload hash mismatch", body["message"])

    def test_execute_route_rejects_unapproved(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        response = self.handler(
            self._req(
                "POST",
                "/v1/chat/execute",
                {
                    "approved": False,
                    "provider": "google_tasks",
                    "action_type": "upsert_grocery_items",
                    "payload": payload,
                    "payload_hash": payload_hash(payload),
                },
            ),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("approval", body["message"])

    # ------------------------------------------------------------------
    # Microsoft calendar dev endpoint — parameter validation
    # ------------------------------------------------------------------

    def test_microsoft_calendar_events_missing_both_params_returns_400(self) -> None:
        """GET /v1/dev/microsoft/calendar/events with no query params must return 400."""
        from unittest.mock import MagicMock

        mock_live_service = MagicMock()
        handler = build_handler(self.config, self.registry, mock_live_service)
        response = handler(self._req("GET", "/v1/dev/microsoft/calendar/events"), None)
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "start and end query parameters are required")
        mock_live_service.list_microsoft_calendar_events.assert_not_called()

    def test_microsoft_calendar_events_missing_end_param_returns_400(self) -> None:
        """GET /v1/dev/microsoft/calendar/events with only start param must return 400."""
        from unittest.mock import MagicMock

        mock_live_service = MagicMock()
        handler = build_handler(self.config, self.registry, mock_live_service)
        response = handler(
            self._req("GET", "/v1/dev/microsoft/calendar/events", query={"start": "2026-04-01T00:00:00Z"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "start and end query parameters are required")
        mock_live_service.list_microsoft_calendar_events.assert_not_called()

    def test_microsoft_calendar_events_missing_start_param_returns_400(self) -> None:
        """GET /v1/dev/microsoft/calendar/events with only end param must return 400."""
        from unittest.mock import MagicMock

        mock_live_service = MagicMock()
        handler = build_handler(self.config, self.registry, mock_live_service)
        response = handler(
            self._req("GET", "/v1/dev/microsoft/calendar/events", query={"end": "2026-04-30T23:59:59Z"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "start and end query parameters are required")
        mock_live_service.list_microsoft_calendar_events.assert_not_called()

    def test_microsoft_calendar_events_with_both_params_delegates_to_service(self) -> None:
        """GET /v1/dev/microsoft/calendar/events with both params calls the service."""
        from unittest.mock import MagicMock

        mock_live_service = MagicMock()
        mock_live_service.list_microsoft_calendar_events.return_value = {
            "events": [],
            "provider": "microsoft_calendar",
        }
        handler = build_handler(self.config, self.registry, mock_live_service)
        response = handler(
            self._req(
                "GET",
                "/v1/dev/microsoft/calendar/events",
                query={"start": "2026-04-01T00:00:00Z", "end": "2026-04-30T23:59:59Z"},
            ),
            None,
        )
        self.assertEqual(response["statusCode"], 200)
        mock_live_service.list_microsoft_calendar_events.assert_called_once_with(
            "2026-04-01T00:00:00Z", "2026-04-30T23:59:59Z"
        )

    def test_execute_returns_502_propagates_for_provider_errors(self) -> None:
        from unittest.mock import patch

        from assistant_app.http_client import HttpRequestError

        with patch(
            "assistant_app.orchestrator.AssistantOrchestrator.execute",
            side_effect=HttpRequestError("upstream error", 502, "bad gateway"),
        ):
            payload = {"list_name": "Groceries", "items": ["milk"]}
            response = self.handler(
                self._req(
                    "POST",
                    "/v1/chat/execute",
                    {
                        "approved": True,
                        "provider": "google_tasks",
                        "action_type": "upsert_grocery_items",
                        "payload": payload,
                        "payload_hash": payload_hash(payload),
                    },
                ),
                None,
            )
            self.assertEqual(response["statusCode"], 502)
