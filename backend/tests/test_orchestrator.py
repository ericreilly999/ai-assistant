from __future__ import annotations

import unittest
from datetime import UTC

from assistant_app.config import AppConfig
from assistant_app.consent import payload_hash
from assistant_app.orchestrator import AssistantOrchestrator
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


class OrchestratorPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = AssistantOrchestrator(_make_config(), ProviderRegistry(mock_mode=True))

    def test_calendar_plan_returns_schedule_text(self) -> None:
        result = self.orchestrator.plan({"message": "What does my day look like tomorrow?"})
        self.assertEqual(result.intent, "calendar")
        self.assertIn("Tomorrow", result.message)
        self.assertGreaterEqual(len(result.sources), 1)
        self.assertTrue(result.warnings)

    def test_calendar_plan_includes_open_windows(self) -> None:
        result = self.orchestrator.plan({"message": "What does my day look like tomorrow?"})
        self.assertIn("Open windows", result.message)

    def test_grocery_plan_returns_confirmation_proposal(self) -> None:
        result = self.orchestrator.plan({"message": "Add milk, eggs and bread to my grocery list"})
        self.assertEqual(result.intent, "grocery")
        self.assertEqual(len(result.proposals), 1)
        self.assertEqual(result.proposals[0].provider, "google_tasks")
        self.assertEqual(result.proposals[0].payload["items"], ["milk", "eggs", "bread"])

    def test_grocery_proposal_has_risk_level(self) -> None:
        result = self.orchestrator.plan({"message": "Add milk to my grocery list"})
        self.assertIn(result.proposals[0].risk_level, {"low", "medium", "high"})

    def test_travel_plan_uses_calendar_provider(self) -> None:
        result = self.orchestrator.plan({"message": "Plan a weekend trip to Miami next month"})
        self.assertEqual(result.intent, "travel")
        self.assertEqual(result.proposals[0].provider, "google_calendar")
        self.assertEqual(result.proposals[0].action_type, "create_calendar_event")

    def test_meeting_prep_plan_returns_document_context(self) -> None:
        result = self.orchestrator.plan({"message": "Prepare me for my architecture review"})
        self.assertEqual(result.intent, "meeting_prep")
        self.assertIn("Referenced documents", result.message)

    def test_tasks_intent_plan(self) -> None:
        result = self.orchestrator.plan({"message": "Complete my work task"})
        self.assertEqual(result.intent, "tasks")
        self.assertEqual(len(result.proposals), 1)
        self.assertIn(result.proposals[0].action_type, {"complete_task", "update_task"})

    def test_general_fallback_returns_helpful_message(self) -> None:
        result = self.orchestrator.plan({"message": "xyz completely unknown request abc"})
        self.assertEqual(result.intent, "general")
        self.assertIn("calendars", result.message)

    def test_providers_filter_respected(self) -> None:
        result = self.orchestrator.plan({
            "message": "Add milk to my grocery list",
            "providers": ["microsoft_todo"],
        })
        self.assertEqual(result.proposals[0].provider, "microsoft_todo")

    def test_meeting_prep_with_calendar_context(self) -> None:
        result = self.orchestrator.plan({
            "message": "Prepare me for my 2pm architecture review",
            "providers": ["google_calendar", "google_drive"],
        })
        self.assertEqual(result.intent, "meeting_prep")
        self.assertGreaterEqual(len(result.sources), 1)


class OrchestratorExecuteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = AssistantOrchestrator(_make_config(), ProviderRegistry(mock_mode=True))

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

    def test_execute_rejects_unapproved(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        with self.assertRaises(ValueError) as ctx:
            self.orchestrator.execute(
                {
                    "approved": False,
                    "provider": "google_tasks",
                    "action_type": "upsert_grocery_items",
                    "payload": payload,
                    "payload_hash": payload_hash(payload),
                }
            )
        self.assertIn("approval", str(ctx.exception))

    def test_execute_rejects_expired_proposal(self) -> None:
        from datetime import datetime

        from assistant_app.consent import build_action_proposal

        payload = {"list_name": "Groceries", "items": ["milk"]}

        past = datetime(2020, 1, 1, tzinfo=UTC)
        proposal = build_action_proposal(
            provider="google_tasks",
            action_type="upsert_grocery_items",
            resource_type="task_list",
            payload=payload,
            summary="Add milk",
            ttl_minutes=15,
            now=past,
        )
        with self.assertRaises(ValueError) as ctx:
            self.orchestrator.execute(
                {
                    "approved": True,
                    "provider": proposal.provider,
                    "action_type": proposal.action_type,
                    "payload": payload,
                    "payload_hash": proposal.payload_hash,
                    "expires_at": proposal.expires_at,
                }
            )
        self.assertIn("expired", str(ctx.exception))

    def test_execute_provider_value_error_propagates(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        with self.assertRaises(ValueError):
            self.orchestrator.execute(
                {
                    "approved": True,
                    "provider": "google_tasks",
                    "action_type": "upsert_grocery_items",
                    "payload": payload,
                    "payload_hash": "wrong-hash",
                }
            )

    def test_execute_receipt_contains_proposal_id(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        result = self.orchestrator.execute(
            {
                "proposal_id": "test-proposal-abc",
                "provider": "google_tasks",
                "action_type": "upsert_grocery_items",
                "approved": True,
                "payload": payload,
                "payload_hash": payload_hash(payload),
            }
        )
        self.assertEqual(result.receipt["proposal_id"], "test-proposal-abc")
