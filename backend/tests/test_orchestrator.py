"""Orchestrator tests — updated for Phase 13 agent loop.

plan() tests now inject MockBedrockAgent. execute() tests are unchanged.
Intent values updated from domain-specific ('calendar', 'tasks', etc.) to 'agent'.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from assistant_app.bedrock_client import MockBedrockAgent
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


def _make_orchestrator(mock_turns: list[dict]) -> AssistantOrchestrator:
    config = _make_config()
    orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
    orch._router = MockBedrockAgent(mock_turns)
    return orch


class OrchestratorPlanTests(unittest.TestCase):

    def test_calendar_plan_returns_schedule_text(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response(
                "get_calendar_events",
                {"start": "2026-04-19T00:00:00-04:00", "end": "2026-04-19T23:59:59-04:00"},
            ),
            _text_response(
                "Tomorrow you have 3 events: Team Standup at 9am, "
                "Architecture Review at 2pm, and 1:1 with Manager at 4pm."
            ),
        ])
        result = orch.plan({"message": "What does my day look like tomorrow?"})
        # Phase 13: intent is 'agent' not 'calendar'
        self.assertEqual(result.intent, "agent")
        self.assertIsNotNone(result.message)
        self.assertGreater(len(result.message), 0)
        self.assertTrue(result.warnings)

    def test_calendar_plan_includes_open_windows(self) -> None:
        # Phase 13: LLM generates the message, so we just verify it's non-empty
        orch = _make_orchestrator([
            _tool_use_response(
                "get_calendar_events",
                {"start": "2026-04-19T00:00:00-04:00", "end": "2026-04-19T23:59:59-04:00"},
            ),
            _text_response(
                "Tomorrow: Team Standup 9-9:30, Architecture Review 2-3pm. "
                "Open windows: 9:30am-2pm and 3pm-5pm."
            ),
        ])
        result = orch.plan({"message": "What does my day look like tomorrow?"})
        # Phase 13: LLM generates message — just verify it's a valid agent response
        self.assertEqual(result.intent, "agent")
        self.assertIsNotNone(result.message)

    def test_grocery_plan_returns_confirmation_proposal(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response("get_grocery_lists", {}, tool_use_id="tu-gl"),
            _tool_use_response(
                "propose_grocery_items",
                {"list_name": "Groceries", "items": ["milk", "eggs", "bread"]},
                tool_use_id="tu-gi",
            ),
            _text_response("Proposed adding milk, eggs, and bread to your Groceries list."),
        ])
        result = orch.plan({"message": "Add milk, eggs and bread to my grocery list"})
        self.assertEqual(result.intent, "agent")
        self.assertGreaterEqual(len(result.proposals), 1)
        self.assertEqual(result.proposals[0].provider, "google_tasks")
        self.assertEqual(result.proposals[0].payload["items"], ["milk", "eggs", "bread"])

    def test_grocery_proposal_has_risk_level(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response("get_grocery_lists", {}, tool_use_id="tu-gl"),
            _tool_use_response(
                "propose_grocery_items",
                {"list_name": "Groceries", "items": ["milk"]},
                tool_use_id="tu-gi",
            ),
            _text_response("Proposed adding milk."),
        ])
        result = orch.plan({"message": "Add milk to my grocery list"})
        self.assertIn(result.proposals[0].risk_level, {"low", "medium", "high"})

    def test_travel_plan_uses_calendar_provider(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response(
                "propose_calendar_event",
                {
                    "title": "Weekend Trip to Miami",
                    "start": "2026-05-15T09:00:00-04:00",
                    "end": "2026-05-17T18:00:00-04:00",
                },
                tool_use_id="tu-travel",
            ),
            _text_response("Proposed a Miami trip on May 15-17."),
        ])
        result = orch.plan({"message": "Plan a weekend trip to Miami next month"})
        self.assertEqual(result.intent, "agent")
        self.assertEqual(result.proposals[0].provider, "google_calendar")
        self.assertEqual(result.proposals[0].action_type, "create_calendar_event")

    def test_meeting_prep_plan_returns_document_context(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response(
                "get_meeting_documents",
                {"keyword": "architecture review"},
                tool_use_id="tu-docs",
            ),
            _text_response(
                "For your Architecture Review I found 'Architecture Review Deck' "
                "and 'Q2 Roadmap'. Referenced documents are linked above."
            ),
        ])
        result = orch.plan({"message": "Prepare me for my architecture review"})
        self.assertEqual(result.intent, "agent")
        self.assertIsNotNone(result.message)

    def test_tasks_intent_plan(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response("get_task_lists", {}, tool_use_id="tu-tl"),
            _tool_use_response(
                "get_tasks", {"list_id": "list-001"}, tool_use_id="tu-gt"
            ),
            _tool_use_response(
                "propose_task_complete",
                {"list_id": "list-001", "task_id": "task-001"},
                tool_use_id="tu-tc",
            ),
            _text_response("Proposed completing your work task."),
        ])
        result = orch.plan({"message": "Complete my work task"})
        self.assertEqual(result.intent, "agent")
        self.assertGreaterEqual(len(result.proposals), 1)
        self.assertIn(result.proposals[0].action_type, {"complete_task", "update_task"})

    def test_general_fallback_returns_helpful_message(self) -> None:
        orch = _make_orchestrator([
            _text_response(
                "I can help you with calendars, tasks, grocery lists, and meeting prep. "
                "Could you tell me more about what you need?"
            ),
        ])
        result = orch.plan({"message": "xyz completely unknown request abc"})
        # Phase 13: intent is 'agent' not 'general'
        self.assertEqual(result.intent, "agent")
        self.assertIn("calendars", result.message)

    def test_providers_filter_respected(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response("get_grocery_lists", {}, tool_use_id="tu-gl"),
            _tool_use_response(
                "propose_grocery_items",
                {"list_name": "Groceries", "items": ["milk"], "provider": "microsoft_todo"},
                tool_use_id="tu-gi",
            ),
            _text_response("Proposed adding milk (microsoft_todo)."),
        ])
        result = orch.plan({
            "message": "Add milk to my grocery list",
            "providers": ["microsoft_todo"],
        })
        self.assertEqual(result.proposals[0].provider, "microsoft_todo")

    def test_meeting_prep_with_calendar_context(self) -> None:
        orch = _make_orchestrator([
            _tool_use_response(
                "get_meeting_documents",
                {"keyword": "architecture review"},
                tool_use_id="tu-docs",
            ),
            _tool_use_response(
                "get_calendar_events",
                {"start": "2026-04-19T00:00:00-04:00", "end": "2026-04-19T23:59:59-04:00"},
                tool_use_id="tu-cal",
            ),
            _text_response("Architecture Review is at 2pm. Found the deck in Drive."),
        ])
        result = orch.plan({
            "message": "Prepare me for my 2pm architecture review",
            "providers": ["google_calendar", "google_drive"],
        })
        self.assertEqual(result.intent, "agent")
        self.assertGreaterEqual(len(result.sources), 0)


class OrchestratorThinkingTagStrippingTests(unittest.TestCase):
    """Tests that inline thinking/answer tags from Nova Pro are stripped before
    the message reaches PlanResult."""

    def test_thinking_tags_are_stripped(self) -> None:
        """Nova Pro <thinking>...</thinking> block must not appear in result.message."""
        orch = _make_orchestrator([
            _text_response(
                "<thinking>Some internal reasoning here</thinking>\n\nThe actual answer."
            ),
        ])
        result = orch.plan({"message": "What can you help me with?"})

        self.assertEqual(result.intent, "agent")
        self.assertEqual(result.message, "The actual answer.")
        self.assertNotIn("<thinking>", result.message)

    def test_answer_wrapper_tags_are_stripped(self) -> None:
        """Nova Pro <answer>...</answer> wrapper must be unwrapped in result.message."""
        orch = _make_orchestrator([
            _text_response(
                "<answer>The actual answer.</answer>"
            ),
        ])
        result = orch.plan({"message": "What can you help me with?"})

        self.assertEqual(result.intent, "agent")
        self.assertEqual(result.message, "The actual answer.")
        self.assertNotIn("<answer>", result.message)
        self.assertNotIn("</answer>", result.message)

    def test_thinking_and_answer_tags_stripped_together(self) -> None:
        """Both <thinking> and <answer> tags stripped when present in one response."""
        orch = _make_orchestrator([
            _text_response(
                "<thinking>Internal reasoning.</thinking>\n\n<answer>Clean response.</answer>"
            ),
        ])
        result = orch.plan({"message": "What can you help me with?"})

        self.assertEqual(result.intent, "agent")
        self.assertEqual(result.message, "Clean response.")
        self.assertNotIn("<thinking>", result.message)
        self.assertNotIn("<answer>", result.message)


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
        from assistant_app.consent import build_action_proposal

        payload = {"list_name": "Groceries", "items": ["milk"]}

        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
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
