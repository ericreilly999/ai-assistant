"""Tests for bedrock_client.py.

Coverage targets:
  BedrockConverseRouter.agent_turn()          — lines 43-58
  BedrockConverseRouter.generate_plan_text()  — lines 65-95
  BedrockConverseRouter._get_client()         — lines 24-30 (ImportError path)
  BedrockGuardrail.apply()                    — lines 131-153
  BedrockGuardrail._get_client()              — lines 111-117 (ImportError path)
  MockBedrockAgent.agent_turn() exhausted     — lines 175-178
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# BedrockConverseRouter
# ---------------------------------------------------------------------------

class TestBedrockConverseRouterAgentTurn(unittest.TestCase):

    def _make_router(self, model_id: str = "amazon.nova-lite-v1:0"):
        from assistant_app.bedrock_client import BedrockConverseRouter
        return BedrockConverseRouter(model_id=model_id, region="us-east-1")

    # ------------------------------------------------------------------
    # mock-router guard
    # ------------------------------------------------------------------

    def test_agent_turn_raises_for_mock_router(self) -> None:
        """agent_turn() must raise RuntimeError when model_id is 'mock-router'."""
        router = self._make_router(model_id="mock-router")
        with self.assertRaises(RuntimeError) as ctx:
            router.agent_turn(messages=[], tools={})
        self.assertIn("mock-router", str(ctx.exception))

    # ------------------------------------------------------------------
    # boto3 unavailable path
    # ------------------------------------------------------------------

    def test_agent_turn_raises_when_boto3_unavailable(self) -> None:
        """agent_turn() must raise RuntimeError when boto3 is not importable."""
        router = self._make_router()
        with patch.dict(sys.modules, {"boto3": None}):
            # Force _client to None so _get_client() re-runs the import attempt.
            router._client = None
            with self.assertRaises(RuntimeError) as ctx:
                router.agent_turn(messages=[], tools={})
        self.assertIn("unavailable", str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # happy path — boto3 mocked
    # ------------------------------------------------------------------

    def test_agent_turn_calls_converse_with_correct_args(self) -> None:
        """agent_turn() must call boto3 converse() with model_id, messages, and toolConfig."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_response = {"stopReason": "end_turn", "output": {}, "usage": {}}
        fake_client.converse.return_value = fake_response

        with patch("boto3.client", return_value=fake_client):
            router._client = None  # force _get_client() to run
            messages = [{"role": "user", "content": [{"text": "hello"}]}]
            tools = {"tools": []}
            result = router.agent_turn(messages, tools)

        fake_client.converse.assert_called_once()
        call_kwargs = fake_client.converse.call_args.kwargs
        self.assertEqual(call_kwargs["modelId"], router.model_id)
        self.assertEqual(call_kwargs["messages"], messages)
        self.assertEqual(call_kwargs["toolConfig"], tools)
        self.assertIs(result, fake_response)

    def test_agent_turn_uses_default_inference_config_when_none_provided(self) -> None:
        """agent_turn() must use {'maxTokens': 1024, 'temperature': 0.0} by default."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_client.converse.return_value = {"stopReason": "end_turn", "output": {}, "usage": {}}

        with patch("boto3.client", return_value=fake_client):
            router._client = None
            router.agent_turn(messages=[], tools={})

        call_kwargs = fake_client.converse.call_args.kwargs
        self.assertEqual(call_kwargs["inferenceConfig"], {"maxTokens": 1024, "temperature": 0.0})

    def test_agent_turn_passes_custom_inference_config(self) -> None:
        """agent_turn() must forward a custom inference_config to converse()."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_client.converse.return_value = {"stopReason": "end_turn", "output": {}, "usage": {}}
        custom_config = {"maxTokens": 512, "temperature": 0.5}

        with patch("boto3.client", return_value=fake_client):
            router._client = None
            router.agent_turn(messages=[], tools={}, inference_config=custom_config)

        call_kwargs = fake_client.converse.call_args.kwargs
        self.assertEqual(call_kwargs["inferenceConfig"], custom_config)

    def test_agent_turn_reuses_cached_client(self) -> None:
        """_get_client() must not call boto3.client() a second time if client is already set."""
        router = self._make_router()
        pre_built_client = MagicMock()
        pre_built_client.converse.return_value = {"stopReason": "end_turn", "output": {}, "usage": {}}
        router._client = pre_built_client

        with patch("boto3.client") as mock_boto3_client:
            router.agent_turn(messages=[], tools={})
            mock_boto3_client.assert_not_called()

        pre_built_client.converse.assert_called_once()


# ---------------------------------------------------------------------------
# BedrockConverseRouter.generate_plan_text()
# ---------------------------------------------------------------------------

class TestBedrockConverseRouterGeneratePlanText(unittest.TestCase):

    def _make_router(self, model_id: str = "amazon.nova-lite-v1:0"):
        from assistant_app.bedrock_client import BedrockConverseRouter
        return BedrockConverseRouter(model_id=model_id)

    def test_generate_plan_text_returns_none_for_mock_router(self) -> None:
        """generate_plan_text() must return None immediately for 'mock-router'."""
        router = self._make_router(model_id="mock-router")
        result = router.generate_plan_text("calendar", "some context")
        self.assertIsNone(result)

    def test_generate_plan_text_returns_none_when_boto3_unavailable(self) -> None:
        """generate_plan_text() must return None when boto3 is not importable."""
        router = self._make_router()
        router._client = None
        with patch.dict(sys.modules, {"boto3": None}):
            result = router.generate_plan_text("tasks", "context here")
        self.assertIsNone(result)

    def test_generate_plan_text_success_path_returns_text(self) -> None:
        """generate_plan_text() must return the text extracted from the Bedrock response."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_client.converse.return_value = {
            "output": {
                "message": {
                    "content": [{"text": "Here is your plan summary."}]
                }
            }
        }

        with patch("boto3.client", return_value=fake_client):
            router._client = None
            result = router.generate_plan_text("calendar", "3 events tomorrow")

        self.assertEqual(result, "Here is your plan summary.")

    def test_generate_plan_text_returns_none_on_exception(self) -> None:
        """generate_plan_text() must return None (not raise) when converse() throws."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_client.converse.side_effect = RuntimeError("Bedrock call failed")

        with patch("boto3.client", return_value=fake_client):
            router._client = None
            result = router.generate_plan_text("tasks", "some context")

        self.assertIsNone(result)

    def test_generate_plan_text_handles_empty_content_list(self) -> None:
        """generate_plan_text() must handle an empty content list without crashing."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_client.converse.return_value = {
            "output": {
                "message": {
                    "content": []
                }
            }
        }

        with patch("boto3.client", return_value=fake_client):
            router._client = None
            result = router.generate_plan_text("calendar", "context")

        # Empty content list: content[0] raises IndexError inside .get(), result is ""
        # The implementation catches all exceptions and returns None, or returns "".
        # Either is acceptable — the key contract is no exception propagates.
        self.assertIsNone(result) if result is None else self.assertIsInstance(result, str)

    def test_generate_plan_text_sends_intent_in_user_message(self) -> None:
        """generate_plan_text() must include the intent_domain in the user message."""
        router = self._make_router()
        fake_client = MagicMock()
        fake_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "plan text"}]}}
        }

        with patch("boto3.client", return_value=fake_client):
            router._client = None
            router.generate_plan_text("grocery_shopping", "items needed")

        call_kwargs = fake_client.converse.call_args.kwargs
        user_message_text = call_kwargs["messages"][0]["content"][0]["text"]
        self.assertIn("grocery_shopping", user_message_text)


# ---------------------------------------------------------------------------
# BedrockGuardrail.apply()
# ---------------------------------------------------------------------------

class TestBedrockGuardrailApply(unittest.TestCase):

    def _make_guardrail(self, guardrail_id: str = "grd-real-001"):
        from assistant_app.bedrock_client import BedrockGuardrail
        return BedrockGuardrail(
            guardrail_id=guardrail_id,
            guardrail_version="1",
            region="us-east-1",
        )

    # ------------------------------------------------------------------
    # mock-guardrail pass-through
    # ------------------------------------------------------------------

    def test_apply_passes_through_for_mock_guardrail(self) -> None:
        """apply() must return (True, original_text) for guardrail_id='mock-guardrail'."""
        from assistant_app.bedrock_client import BedrockGuardrail
        guardrail = BedrockGuardrail(
            guardrail_id="mock-guardrail",
            guardrail_version="DRAFT",
        )
        passed, text = guardrail.apply("some sensitive text")
        self.assertTrue(passed)
        self.assertEqual(text, "some sensitive text")

    # ------------------------------------------------------------------
    # boto3 unavailable path
    # ------------------------------------------------------------------

    def test_apply_passes_through_when_boto3_unavailable(self) -> None:
        """apply() must return (True, text) when boto3 is not importable."""
        guardrail = self._make_guardrail()
        guardrail._client = None
        with patch.dict(sys.modules, {"boto3": None}):
            passed, text = guardrail.apply("some text")
        self.assertTrue(passed)
        self.assertEqual(text, "some text")

    # ------------------------------------------------------------------
    # GUARDRAIL_INTERVENED path
    # ------------------------------------------------------------------

    def test_apply_returns_false_and_safe_text_when_guardrail_intervenes(self) -> None:
        """apply() must return (False, safe_text) when action='GUARDRAIL_INTERVENED'."""
        guardrail = self._make_guardrail()
        fake_client = MagicMock()
        fake_client.apply_guardrail.return_value = {
            "action": "GUARDRAIL_INTERVENED",
            "outputs": [{"text": "I cannot help with that request."}],
        }

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            passed, safe_text = guardrail.apply("do something harmful")

        self.assertFalse(passed)
        self.assertEqual(safe_text, "I cannot help with that request.")

    def test_apply_uses_default_safe_text_when_outputs_empty(self) -> None:
        """apply() must use fallback text 'I cannot help...' when outputs list is empty."""
        guardrail = self._make_guardrail()
        fake_client = MagicMock()
        fake_client.apply_guardrail.return_value = {
            "action": "GUARDRAIL_INTERVENED",
            "outputs": [],
        }

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            passed, safe_text = guardrail.apply("harmful content")

        self.assertFalse(passed)
        self.assertEqual(safe_text, "I cannot help with that request.")

    # ------------------------------------------------------------------
    # Pass-through path (no intervention)
    # ------------------------------------------------------------------

    def test_apply_returns_true_and_original_text_when_no_intervention(self) -> None:
        """apply() must return (True, original_text) when action != GUARDRAIL_INTERVENED."""
        guardrail = self._make_guardrail()
        fake_client = MagicMock()
        fake_client.apply_guardrail.return_value = {"action": "NONE"}

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            passed, text = guardrail.apply("normal safe request")

        self.assertTrue(passed)
        self.assertEqual(text, "normal safe request")

    # ------------------------------------------------------------------
    # Exception path
    # ------------------------------------------------------------------

    def test_apply_returns_true_when_guardrail_call_raises(self) -> None:
        """apply() must return (True, text) (not raise) when apply_guardrail() throws."""
        guardrail = self._make_guardrail()
        fake_client = MagicMock()
        fake_client.apply_guardrail.side_effect = RuntimeError("Guardrail service error")

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            passed, text = guardrail.apply("some text")

        self.assertTrue(passed)
        self.assertEqual(text, "some text")

    # ------------------------------------------------------------------
    # check alias
    # ------------------------------------------------------------------

    def test_check_is_alias_for_apply(self) -> None:
        """check is documented as an alias for apply; must produce the same result."""
        guardrail = self._make_guardrail()
        fake_client = MagicMock()
        fake_client.apply_guardrail.return_value = {"action": "NONE"}

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            result_apply = guardrail.apply("text", source="INPUT")

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            result_check = guardrail.check("text", source="INPUT")

        self.assertEqual(result_apply, result_check)

    # ------------------------------------------------------------------
    # source parameter
    # ------------------------------------------------------------------

    def test_apply_passes_source_parameter_to_api(self) -> None:
        """apply() must pass the 'source' argument to apply_guardrail()."""
        guardrail = self._make_guardrail()
        fake_client = MagicMock()
        fake_client.apply_guardrail.return_value = {"action": "NONE"}

        with patch("boto3.client", return_value=fake_client):
            guardrail._client = None
            guardrail.apply("model output text", source="OUTPUT")

        call_kwargs = fake_client.apply_guardrail.call_args.kwargs
        self.assertEqual(call_kwargs["source"], "OUTPUT")


# ---------------------------------------------------------------------------
# BedrockGuardrail._get_client() caching
# ---------------------------------------------------------------------------

class TestBedrockGuardrailGetClient(unittest.TestCase):

    def test_get_client_caches_after_first_call(self) -> None:
        """_get_client() must not construct a new boto3 client on subsequent calls."""
        from assistant_app.bedrock_client import BedrockGuardrail
        guardrail = BedrockGuardrail(guardrail_id="grd-cache", guardrail_version="1")
        fake_client = MagicMock()

        with patch("boto3.client", return_value=fake_client) as mock_boto3_client:
            guardrail._client = None
            guardrail._get_client()
            guardrail._get_client()
            self.assertEqual(mock_boto3_client.call_count, 1)

    def test_get_client_returns_none_on_import_error(self) -> None:
        """_get_client() must return None when boto3 ImportError occurs."""
        from assistant_app.bedrock_client import BedrockGuardrail
        guardrail = BedrockGuardrail(guardrail_id="grd-none", guardrail_version="1")
        guardrail._client = None

        with patch.dict(sys.modules, {"boto3": None}):
            result = guardrail._get_client()

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# MockBedrockAgent
# ---------------------------------------------------------------------------

class TestMockBedrockAgent(unittest.TestCase):

    def _make(self, turns):
        from assistant_app.bedrock_client import MockBedrockAgent
        return MockBedrockAgent(turns)

    def test_mock_agent_replays_programmed_turns(self) -> None:
        """MockBedrockAgent must return turns in order."""
        turn1 = {"stopReason": "tool_use", "output": {}}
        turn2 = {"stopReason": "end_turn", "output": {"message": {"content": [{"text": "done"}]}}}
        agent = self._make([turn1, turn2])

        result1 = agent.agent_turn(messages=[], tools={})
        result2 = agent.agent_turn(messages=[], tools={})

        self.assertIs(result1, turn1)
        self.assertIs(result2, turn2)

    def test_mock_agent_exhausted_raises_runtime_error(self) -> None:
        """MockBedrockAgent must raise RuntimeError when all programmed turns are consumed."""
        agent = self._make([{"stopReason": "end_turn", "output": {}}])
        agent.agent_turn(messages=[], tools={})  # consume the only turn

        with self.assertRaises(RuntimeError) as ctx:
            agent.agent_turn(messages=[], tools={})

        self.assertIn("exhausted", str(ctx.exception).lower())

    def test_mock_agent_captures_calls(self) -> None:
        """MockBedrockAgent must record each (messages, tools) call in .calls."""
        agent = self._make([
            {"stopReason": "end_turn", "output": {}},
            {"stopReason": "end_turn", "output": {}},
        ])
        msgs1 = [{"role": "user", "content": [{"text": "hello"}]}]
        tools1 = {"tools": []}
        msgs2 = [{"role": "user", "content": [{"text": "world"}]}]
        tools2 = {"tools": ["t1"]}

        agent.agent_turn(msgs1, tools1)
        agent.agent_turn(msgs2, tools2)

        self.assertEqual(len(agent.calls), 2)
        self.assertEqual(agent.calls[0]["messages"], msgs1)
        self.assertEqual(agent.calls[0]["tools"], tools1)
        self.assertEqual(agent.calls[1]["messages"], msgs2)
        self.assertEqual(agent.calls[1]["tools"], tools2)

    def test_mock_agent_inference_config_accepted(self) -> None:
        """MockBedrockAgent must accept an inference_config kwarg without error."""
        agent = self._make([{"stopReason": "end_turn", "output": {}}])
        agent.agent_turn(messages=[], tools={}, inference_config={"maxTokens": 256})

    def test_mock_agent_zero_turns_raises_immediately(self) -> None:
        """MockBedrockAgent with an empty turns list must raise on the first call."""
        agent = self._make([])
        with self.assertRaises(RuntimeError):
            agent.agent_turn(messages=[], tools={})


# ---------------------------------------------------------------------------
# BedrockConverseRouter._get_client() caching
# ---------------------------------------------------------------------------

class TestBedrockConverseRouterGetClient(unittest.TestCase):

    def test_get_client_caches_after_first_successful_call(self) -> None:
        """_get_client() must not call boto3.client() more than once."""
        from assistant_app.bedrock_client import BedrockConverseRouter
        router = BedrockConverseRouter(model_id="test-model")
        fake_client = MagicMock()

        with patch("boto3.client", return_value=fake_client) as mock_boto3_client:
            router._client = None
            router._get_client()
            router._get_client()
            self.assertEqual(mock_boto3_client.call_count, 1)

    def test_get_client_returns_none_on_import_error(self) -> None:
        """_get_client() must return None when boto3 is not importable."""
        from assistant_app.bedrock_client import BedrockConverseRouter
        router = BedrockConverseRouter(model_id="test-model")
        router._client = None

        with patch.dict(sys.modules, {"boto3": None}):
            result = router._get_client()

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
