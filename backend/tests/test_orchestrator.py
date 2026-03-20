from __future__ import annotations

import unittest

from assistant_app.config import AppConfig
from assistant_app.consent import payload_hash
from assistant_app.orchestrator import AssistantOrchestrator
from assistant_app.registry import ProviderRegistry


class OrchestratorTests(unittest.TestCase):
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
        self.orchestrator = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))

    def test_calendar_plan_returns_schedule_text(self) -> None:
        result = self.orchestrator.plan({"message": "What does my day look like tomorrow?"})

        self.assertEqual(result.intent, "calendar")
        self.assertIn("Tomorrow", result.message)
        self.assertGreaterEqual(len(result.sources), 1)
        self.assertTrue(result.warnings)

    def test_grocery_plan_returns_confirmation_proposal(self) -> None:
        result = self.orchestrator.plan({"message": "Add milk, eggs and bread to my grocery list"})

        self.assertEqual(result.intent, "grocery")
        self.assertEqual(len(result.proposals), 1)
        self.assertEqual(result.proposals[0].provider, "google_tasks")
        self.assertEqual(result.proposals[0].payload["items"], ["milk", "eggs", "bread"])

    def test_travel_plan_uses_calendar_provider(self) -> None:
        result = self.orchestrator.plan({"message": "Plan a weekend trip to Miami next month"})

        self.assertEqual(result.intent, "travel")
        self.assertEqual(result.proposals[0].provider, "google_calendar")
        self.assertEqual(result.proposals[0].action_type, "create_calendar_event")

    def test_execute_returns_mock_receipt(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        result = self.orchestrator.execute(
            {
                "proposal_id": "proposal-1",
                "provider": "google_tasks",
                "action_type": "upsert_grocery_items",
                "approved": True,
                "payload": payload,
                "payload_hash": payload_hash(payload),
            }
        )

        self.assertEqual(result.provider, "google_tasks")
        self.assertEqual(result.receipt["mode"], "mock")