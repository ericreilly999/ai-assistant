from __future__ import annotations

import json
import unittest

from assistant_app.config import AppConfig
from assistant_app.handler import build_handler
from assistant_app.registry import ProviderRegistry


class HandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        config = AppConfig(
            app_env="dev",
            log_level="INFO",
            mock_provider_mode=True,
            proposal_ttl_minutes=15,
            default_timezone="America/New_York",
            bedrock_router_model_id="mock-router",
            bedrock_guardrail_id="mock-guardrail",
            bedrock_guardrail_version="DRAFT",
        )
        self.handler = build_handler(config, ProviderRegistry(mock_mode=True))

    def test_health_route(self) -> None:
        response = self.handler({"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}, None)
        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["environment"], "dev")
        self.assertTrue(body["mock_provider_mode"])

    def test_plan_route(self) -> None:
        response = self.handler(
            {
                "rawPath": "/v1/chat/plan",
                "requestContext": {"http": {"method": "POST"}},
                "body": json.dumps({"message": "Add bananas to my grocery list"}),
            },
            None,
        )
        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["intent"], "grocery")
        self.assertEqual(len(body["proposals"]), 1)

    def test_execute_route_rejects_invalid_hash(self) -> None:
        response = self.handler(
            {
                "rawPath": "/v1/chat/execute",
                "requestContext": {"http": {"method": "POST"}},
                "body": json.dumps(
                    {
                        "approved": True,
                        "provider": "google_tasks",
                        "action_type": "upsert_grocery_items",
                        "payload": {"items": ["milk"]},
                        "payload_hash": "bad-hash",
                    }
                ),
            },
            None,
        )
        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Payload hash mismatch", body["message"])