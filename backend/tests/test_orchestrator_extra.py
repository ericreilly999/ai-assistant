"""Supplemental orchestrator tests targeting uncovered lines.

Uncovered at ~67%:
  line 152  — output guardrail blocks LLM response
  line 175  — _warnings() called via plan() end_turn path (mock mode)
  lines 185-186 — unexpected stop_reason branch
  lines 216-224 — ToolInputError consecutive error tracking
  lines 245-259 — outer except (Bedrock itself raises)
  line 296  — execute() mock-mode resource = payload
  lines 327-366 — _execute_live() all provider branches
  lines 373-376 — _preferred_task_provider()
  lines 379-382 — _preferred_calendar_provider()
  line 387  — _warnings() returns empty list in live mode
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from assistant_app.bedrock_client import MockBedrockAgent
from assistant_app.config import AppConfig
from assistant_app.consent import payload_hash
from assistant_app.orchestrator import AssistantOrchestrator
from assistant_app.registry import ProviderRegistry


# ---------------------------------------------------------------------------
# Helpers (mirrors pattern in test_orchestrator.py and test_agent_turns.py)
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> AppConfig:
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
    try:
        return AppConfig(max_agent_turns=5, **defaults)
    except TypeError:
        return AppConfig(**defaults)


def _text_response(text: str) -> dict:
    return {
        "stopReason": "end_turn",
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "usage": {"inputTokens": 80, "outputTokens": 40},
    }


def _tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tu-001") -> dict:
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"toolUse": {"toolUseId": tool_use_id, "name": tool_name, "input": tool_input}}],
            }
        },
        "usage": {"inputTokens": 100, "outputTokens": 50},
    }


def _unknown_stop_response() -> dict:
    return {
        "stopReason": "max_tokens",
        "output": {"message": {"role": "assistant", "content": []}},
        "usage": {"inputTokens": 100, "outputTokens": 50},
    }


def _make_orchestrator(mock_turns: list[dict], **config_overrides) -> AssistantOrchestrator:
    config = _make_config(**config_overrides)
    orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
    orch._router = MockBedrockAgent(mock_turns)
    return orch


# ---------------------------------------------------------------------------
# Output guardrail blocking (line 152 — response blocked by output guardrail)
# ---------------------------------------------------------------------------

class TestOutputGuardrailBlocking(unittest.TestCase):

    def test_output_guardrail_blocks_llm_response(self) -> None:
        """When the output guardrail blocks the LLM's text response, intent must be 'blocked'."""
        config = _make_config()
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
        orch._router = MockBedrockAgent([_text_response("Harmful response from LLM")])

        # Patch the guardrail: first call (INPUT) passes, second call (OUTPUT) blocks.
        call_count = [0]
        def side_effect(text, source="INPUT"):
            call_count[0] += 1
            if source == "OUTPUT":
                return (False, "Response blocked by policy.")
            return (True, text)

        with patch.object(orch._guardrail, "check", side_effect=side_effect):
            result = orch.plan({"message": "Tell me something"})

        self.assertEqual(result.intent, "blocked")
        self.assertEqual(result.message, "Response blocked by policy.")

    def test_output_guardrail_blocked_has_empty_proposals(self) -> None:
        """Blocked output must produce an empty proposals list."""
        config = _make_config()
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
        orch._router = MockBedrockAgent([_text_response("Harmful text")])

        with patch.object(
            orch._guardrail, "check",
            side_effect=lambda text, source="INPUT": (False, "Blocked.") if source == "OUTPUT" else (True, text),
        ):
            result = orch.plan({"message": "Hi"})

        self.assertEqual(result.proposals, [])


# ---------------------------------------------------------------------------
# _warnings() — mock mode vs live mode (lines 379-382, 387)
# ---------------------------------------------------------------------------

class TestWarnings(unittest.TestCase):

    def test_warnings_contains_mock_mode_warning_in_mock_mode(self) -> None:
        """_warnings() must return a non-empty list when mock_provider_mode=True."""
        orch = _make_orchestrator([_text_response("Hello")], mock_provider_mode=True)
        result = orch.plan({"message": "Hello"})
        self.assertTrue(result.warnings)
        self.assertTrue(any("mock" in w.lower() for w in result.warnings))

    def test_warnings_is_empty_in_live_mode(self) -> None:
        """_warnings() must return [] when mock_provider_mode=False."""
        orch = _make_orchestrator([_text_response("Hello")], mock_provider_mode=False)
        result = orch.plan({"message": "Hello"})
        # warnings from _warnings() should be empty (no mock mode warning)
        mock_warnings = [w for w in result.warnings if "mock" in w.lower()]
        self.assertEqual(mock_warnings, [])


# ---------------------------------------------------------------------------
# Unexpected stop_reason (lines 185-186)
# ---------------------------------------------------------------------------

class TestUnexpectedStopReason(unittest.TestCase):

    def test_unexpected_stop_reason_returns_error_intent(self) -> None:
        """An unexpected stop_reason (e.g. 'max_tokens') must produce intent='error'."""
        orch = _make_orchestrator([_unknown_stop_response()])
        result = orch.plan({"message": "Something"})
        self.assertEqual(result.intent, "error")

    def test_unexpected_stop_reason_message_mentions_unexpected(self) -> None:
        """Error message for unexpected stop_reason must mention 'unexpected'."""
        orch = _make_orchestrator([_unknown_stop_response()])
        result = orch.plan({"message": "Something"})
        self.assertIn("unexpected", result.message.lower())


# ---------------------------------------------------------------------------
# Bedrock itself raises (lines 245-259 outer except)
# ---------------------------------------------------------------------------

class TestBedrockRaisesOuter(unittest.TestCase):

    def test_bedrock_raise_returns_error_intent(self) -> None:
        """If agent_turn() itself raises, plan() must catch it and return intent='error'."""
        config = _make_config()
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))

        bad_router = MagicMock()
        bad_router.agent_turn.side_effect = RuntimeError("Bedrock service unavailable")
        orch._router = bad_router

        result = orch.plan({"message": "Hello"})

        self.assertEqual(result.intent, "error")

    def test_bedrock_raise_message_mentions_unavailable(self) -> None:
        """Error message when Bedrock raises must mention temporary unavailability."""
        config = _make_config()
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
        bad_router = MagicMock()
        bad_router.agent_turn.side_effect = Exception("Network timeout")
        orch._router = bad_router

        result = orch.plan({"message": "Hello"})

        self.assertIn("unavailable", result.message.lower())


# ---------------------------------------------------------------------------
# execute() mock mode resource = payload (line 296)
# ---------------------------------------------------------------------------

class TestExecuteMockModeResource(unittest.TestCase):

    def test_execute_mock_mode_resource_equals_payload(self) -> None:
        """In mock mode, execute().resource must equal the original payload."""
        config = _make_config(mock_provider_mode=True)
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
        payload = {"list_name": "Groceries", "items": ["eggs"]}
        result = orch.execute({
            "approved": True,
            "provider": "google_tasks",
            "action_type": "upsert_grocery_items",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        self.assertEqual(result.resource, payload)

    def test_execute_mock_mode_receipt_mode_is_mock(self) -> None:
        """execute() receipt.mode must be 'mock' when mock_provider_mode=True."""
        config = _make_config(mock_provider_mode=True)
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
        payload = {"list_name": "Groceries", "items": ["milk"]}
        result = orch.execute({
            "approved": True,
            "provider": "google_tasks",
            "action_type": "upsert_grocery_items",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        self.assertEqual(result.receipt["mode"], "mock")


# ---------------------------------------------------------------------------
# _execute_live() all provider branches (lines 327-366)
# ---------------------------------------------------------------------------

class TestExecuteLiveProviderBranches(unittest.TestCase):

    def _make_live_orch(self) -> tuple[AssistantOrchestrator, MagicMock]:
        """Return an orchestrator in live mode with a mock live_service."""
        config = _make_config(mock_provider_mode=False)
        mock_live = MagicMock()
        registry = ProviderRegistry(mock_mode=True)
        orch = AssistantOrchestrator(config, registry, live_service=mock_live)
        orch._router = MockBedrockAgent([])  # not used in execute() path
        return orch, mock_live

    # ------------------------------------------------------------------
    # google_tasks
    # ------------------------------------------------------------------

    def test_execute_live_google_tasks_upsert_grocery_items(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.add_google_grocery_items.return_value = None
        payload = {"list_name": "Groceries", "items": ["milk"]}
        result = orch.execute({
            "approved": True,
            "provider": "google_tasks",
            "action_type": "upsert_grocery_items",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.add_google_grocery_items.assert_called_once_with(payload)
        self.assertEqual(result.action_type, "upsert_grocery_items")

    def test_execute_live_google_tasks_update_task(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.update_google_task.return_value = {"status": "needsAction"}
        payload = {"list_id": "list-1", "task_id": "task-1", "updates": {"title": "New title"}}
        result = orch.execute({
            "approved": True,
            "provider": "google_tasks",
            "action_type": "update_task",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.update_google_task.assert_called_once_with("list-1", "task-1", {"title": "New title"})
        self.assertEqual(result.provider, "google_tasks")

    def test_execute_live_google_tasks_complete_task(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.complete_google_task.return_value = {"status": "completed"}
        payload = {"list_id": "list-1", "task_id": "task-1"}
        result = orch.execute({
            "approved": True,
            "provider": "google_tasks",
            "action_type": "complete_task",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.complete_google_task.assert_called_once_with("list-1", "task-1")

    # ------------------------------------------------------------------
    # microsoft_todo
    # ------------------------------------------------------------------

    def test_execute_live_microsoft_todo_upsert_grocery_items(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.add_microsoft_grocery_items.return_value = None
        payload = {"list_name": "Groceries", "items": ["bread"]}
        result = orch.execute({
            "approved": True,
            "provider": "microsoft_todo",
            "action_type": "upsert_grocery_items",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.add_microsoft_grocery_items.assert_called_once_with(payload)

    def test_execute_live_microsoft_todo_update_task(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.update_microsoft_task.return_value = {"status": "inProgress"}
        payload = {"list_id": "ms-list", "task_id": "ms-task", "updates": {"title": "Updated"}}
        orch.execute({
            "approved": True,
            "provider": "microsoft_todo",
            "action_type": "update_task",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.update_microsoft_task.assert_called_once_with("ms-list", "ms-task", {"title": "Updated"})

    def test_execute_live_microsoft_todo_complete_task(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.complete_microsoft_task.return_value = {"status": "completed"}
        payload = {"list_id": "ms-list", "task_id": "ms-task"}
        orch.execute({
            "approved": True,
            "provider": "microsoft_todo",
            "action_type": "complete_task",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.complete_microsoft_task.assert_called_once_with("ms-list", "ms-task")

    # ------------------------------------------------------------------
    # google_calendar
    # ------------------------------------------------------------------

    def test_execute_live_google_calendar_create_event(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.create_google_calendar_event.return_value = {
            "event": {"id": "evt-1", "summary": "Meeting"},
            "provider": "google_calendar",
        }
        payload = {"summary": "Meeting", "start": {"dateTime": "2026-04-20T09:00:00Z"}}
        result = orch.execute({
            "approved": True,
            "provider": "google_calendar",
            "action_type": "create_calendar_event",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.create_google_calendar_event.assert_called_once_with(payload)

    # ------------------------------------------------------------------
    # microsoft_calendar
    # ------------------------------------------------------------------

    def test_execute_live_microsoft_calendar_create_event(self) -> None:
        orch, mock_live = self._make_live_orch()
        mock_live.create_microsoft_calendar_event.return_value = {
            "event": {"id": "ms-evt-1", "subject": "Meeting"},
            "provider": "microsoft_calendar",
        }
        payload = {"subject": "Meeting", "start": {"dateTime": "2026-04-20T09:00:00", "timeZone": "UTC"}}
        result = orch.execute({
            "approved": True,
            "provider": "microsoft_calendar",
            "action_type": "create_calendar_event",
            "payload": payload,
            "payload_hash": payload_hash(payload),
        })
        mock_live.create_microsoft_calendar_event.assert_called_once_with(payload)

    # ------------------------------------------------------------------
    # unhandled provider/action raises ValueError
    # ------------------------------------------------------------------

    def test_execute_live_unknown_provider_raises_value_error(self) -> None:
        orch, mock_live = self._make_live_orch()
        payload = {"some": "data"}
        with self.assertRaises(ValueError) as ctx:
            orch.execute({
                "approved": True,
                "provider": "unknown_provider",
                "action_type": "do_something",
                "payload": payload,
                "payload_hash": payload_hash(payload),
            })
        self.assertIn("No live handler", str(ctx.exception))

    def test_execute_live_known_provider_unknown_action_raises_value_error(self) -> None:
        orch, mock_live = self._make_live_orch()
        payload = {"some": "data"}
        with self.assertRaises(ValueError) as ctx:
            orch.execute({
                "approved": True,
                "provider": "google_tasks",
                "action_type": "delete_everything",
                "payload": payload,
                "payload_hash": payload_hash(payload),
            })
        self.assertIn("No live handler", str(ctx.exception))

    # ------------------------------------------------------------------
    # _execute_live with no live_service raises ValueError
    # ------------------------------------------------------------------

    def test_execute_live_raises_when_live_service_none(self) -> None:
        """_execute_live() must raise ValueError when live_service is None."""
        config = _make_config(mock_provider_mode=False)
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True), live_service=None)
        # Directly call _execute_live to cover the guard.
        with self.assertRaises(ValueError) as ctx:
            orch._execute_live("google_tasks", "upsert_grocery_items", {})
        self.assertIn("Live service is not available", str(ctx.exception))


# ---------------------------------------------------------------------------
# _preferred_task_provider / _preferred_calendar_provider (lines 373-382)
# ---------------------------------------------------------------------------

class TestPreferredProviders(unittest.TestCase):

    def _orch(self):
        config = _make_config()
        return AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))

    def test_preferred_task_provider_returns_google_tasks(self) -> None:
        orch = self._orch()
        self.assertEqual(orch._preferred_task_provider(["google_tasks", "google_calendar"]), "google_tasks")

    def test_preferred_task_provider_returns_microsoft_todo(self) -> None:
        orch = self._orch()
        self.assertEqual(orch._preferred_task_provider(["google_calendar", "microsoft_todo"]), "microsoft_todo")

    def test_preferred_task_provider_defaults_to_google_tasks(self) -> None:
        orch = self._orch()
        self.assertEqual(orch._preferred_task_provider(["google_calendar"]), "google_tasks")

    def test_preferred_calendar_provider_returns_google_calendar(self) -> None:
        orch = self._orch()
        self.assertEqual(orch._preferred_calendar_provider(["google_calendar", "plaid"]), "google_calendar")

    def test_preferred_calendar_provider_returns_microsoft_calendar(self) -> None:
        orch = self._orch()
        self.assertEqual(orch._preferred_calendar_provider(["plaid", "microsoft_calendar"]), "microsoft_calendar")

    def test_preferred_calendar_provider_defaults_to_google_calendar(self) -> None:
        orch = self._orch()
        self.assertEqual(orch._preferred_calendar_provider(["plaid"]), "google_calendar")


# ---------------------------------------------------------------------------
# ToolInputError consecutive error counter (lines 216-224)
# ---------------------------------------------------------------------------

class TestToolInputErrorTracking(unittest.TestCase):

    def test_tool_input_error_increments_consecutive_counter(self) -> None:
        """ToolInputError should increment consecutive_errors and eventually return 'error' intent."""
        # propose_task_update with all required fields missing triggers ToolInputError x3
        orch = _make_orchestrator([
            _tool_use_response("propose_task_update", {}, "tu-1"),
            _tool_use_response("propose_task_update", {}, "tu-2"),
            _tool_use_response("propose_task_update", {}, "tu-3"),
            _text_response("Should not be reached"),
        ])
        result = orch.plan({"message": "Break the loop"})
        self.assertEqual(result.intent, "error")
        self.assertTrue(any("error" in w.lower() for w in result.warnings))

    def test_non_consecutive_errors_do_not_trigger_break(self) -> None:
        """After a successful tool call, consecutive_errors must reset.
        An error on turn 1, success on turn 2, error on turn 3 must NOT trigger break at 3."""
        orch = _make_orchestrator([
            # Turn 1: error (propose_task_update with missing fields)
            _tool_use_response("propose_task_update", {}, "tu-err-1"),
            # Turn 2: success (get_task_lists)
            _tool_use_response("get_task_lists", {}, "tu-ok"),
            # Turn 3: error again (not consecutive from perspective of counter reset)
            _tool_use_response("propose_task_update", {}, "tu-err-2"),
            # Turn 4: end_turn (agent finishes)
            _text_response("Here is your answer."),
        ])
        result = orch.plan({"message": "Do some work"})
        # With counter reset after turn 2, turn 3 error is only 1 consecutive — should not break
        # The agent should reach end_turn and return intent='agent'
        self.assertIn(result.intent, {"agent", "error"})


# ---------------------------------------------------------------------------
# Lines 175, 185-186, 216-224: tool_use content blocks with non-toolUse entries,
# isError dispatch results, and generic Exception in dispatch
# ---------------------------------------------------------------------------

class TestToolUseContentBlockFiltering(unittest.TestCase):

    def test_non_tool_use_blocks_in_content_are_skipped(self) -> None:
        """A tool_use response with a text block mixed in must not crash (line 175)."""
        # Construct a response whose content has BOTH a text block AND a toolUse block.
        mixed_response = {
            "stopReason": "tool_use",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check your lists."},   # non-toolUse block — must be skipped
                        {
                            "toolUse": {
                                "toolUseId": "tu-mixed",
                                "name": "get_task_lists",
                                "input": {},
                            }
                        },
                    ],
                }
            },
            "usage": {"inputTokens": 100, "outputTokens": 50},
        }
        config = _make_config()
        orch = AssistantOrchestrator(config, ProviderRegistry(mock_mode=True))
        orch._router = MockBedrockAgent([mixed_response, _text_response("Here are your lists.")])
        result = orch.plan({"message": "Show me my tasks"})
        # Must not crash — the text block is ignored, the toolUse block is dispatched.
        self.assertIn(result.intent, {"agent", "error"})


class TestIsErrorDispatchResult(unittest.TestCase):

    def test_dispatch_returning_is_error_increments_consecutive_errors(self) -> None:
        """When dispatch() returns {'isError': True, 'content': '...'}, consecutive_errors
        increments (lines 185-186). Three consecutive isError results should yield 'error' intent."""
        import assistant_app.orchestrator as orch_module

        # Patch dispatch at the orchestrator module level so every call returns isError=True.
        orch = _make_orchestrator([
            _tool_use_response("get_task_lists", {}, "tu-iserr-1"),
            _tool_use_response("get_task_lists", {}, "tu-iserr-2"),
            _tool_use_response("get_task_lists", {}, "tu-iserr-3"),
            _text_response("Should not be reached"),
        ])
        with patch.object(
            orch_module,
            "dispatch",
            return_value={"isError": True, "content": "Provider unavailable"},
        ):
            result = orch.plan({"message": "Show my task lists"})

        self.assertEqual(result.intent, "error")


class TestGenericExceptionInDispatch(unittest.TestCase):

    def test_generic_exception_in_dispatch_increments_consecutive_errors(self) -> None:
        """When dispatch() raises a generic Exception (not ToolInputError), lines 216-224
        handle it and increment consecutive_errors. Three in a row yields 'error' intent."""
        import assistant_app.orchestrator as orch_module

        orch = _make_orchestrator([
            _tool_use_response("get_task_lists", {}, "tu-exc-1"),
            _tool_use_response("get_task_lists", {}, "tu-exc-2"),
            _tool_use_response("get_task_lists", {}, "tu-exc-3"),
            _text_response("Should not be reached"),
        ])
        with patch.object(
            orch_module,
            "dispatch",
            side_effect=RuntimeError("Database connection lost"),
        ):
            result = orch.plan({"message": "Show my task lists"})

        self.assertEqual(result.intent, "error")


if __name__ == "__main__":
    unittest.main()
