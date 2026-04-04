from __future__ import annotations

import json
import unittest

from assistant_app.config import AppConfig
from assistant_app.consent import payload_hash
from assistant_app.handler import build_handler
from assistant_app.registry import ProviderRegistry


def _make_config(**overrides):
    defaults = dict(
        app_env="dev",
        log_level="INFO",
        mock_provider_mode=True,
        proposal_ttl_minutes=15,
        default_timezone="America/New_York",
        bedrock_router_model_id="mock-router",
        bedrock_guardrail_id="mock-guardrail",
        bedrock_guardrail_version="DRAFT",
    )
    defaults.update(overrides)
    return AppConfig(**defaults)


class HandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = build_handler(_make_config(), ProviderRegistry(mock_mode=True))

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
        # No Google credentials configured → 400 with HTML error page
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Not Configured", response["body"])

    def test_microsoft_oauth_start_redirects_when_not_configured(self) -> None:
        response = self.handler(self._req("GET", "/oauth/microsoft/start"), None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Not Configured", response["body"])

    # ------------------------------------------------------------------
    # Plan routes
    # ------------------------------------------------------------------

    def test_plan_route_grocery(self) -> None:
        response = self.handler(
            self._req("POST", "/v1/chat/plan", {"message": "Add bananas to my grocery list"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["intent"], "grocery")
        self.assertEqual(len(body["proposals"]), 1)

    def test_plan_route_calendar(self) -> None:
        response = self.handler(
            self._req("POST", "/v1/chat/plan", {"message": "What does my day look like tomorrow?"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["intent"], "calendar")
        self.assertIn("Tomorrow", body["message"])

    def test_plan_route_meeting_prep(self) -> None:
        response = self.handler(
            self._req("POST", "/v1/chat/plan", {"message": "Prepare me for my architecture review"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["intent"], "meeting_prep")

    def test_plan_route_tasks_intent(self) -> None:
        response = self.handler(
            self._req("POST", "/v1/chat/plan", {"message": "Complete my task"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["intent"], "tasks")

    def test_plan_route_general_fallback_returns_helpful_message(self) -> None:
        response = self.handler(
            self._req("POST", "/v1/chat/plan", {"message": "something completely unrecognized xyz"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["intent"], "general")
        self.assertIn("calendars", body["message"])

    def test_plan_route_warnings_present_in_mock_mode(self) -> None:
        response = self.handler(
            self._req("POST", "/v1/chat/plan", {"message": "What does my day look like tomorrow?"}),
            None,
        )
        body = json.loads(response["body"])
        self.assertTrue(len(body["warnings"]) > 0)

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

    def test_execute_returns_502_propagates_for_provider_errors(self) -> None:
        # HttpRequestError with status_code propagates to 502 by default
        # This is tested indirectly via the handler's except clause
        # (direct unit test; no live network call needed)
        from assistant_app.http_client import HttpRequestError
        from unittest.mock import patch

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
