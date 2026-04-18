from __future__ import annotations

import logging
from typing import Any

from assistant_app.tool_definitions import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class BedrockConverseRouter:
    """Routes user messages through the Bedrock Converse API for plan generation.

    In mock mode (when boto3 is unavailable or bedrock_router_model_id == "mock-router")
    Bedrock calls return None or raise RuntimeError as appropriate.
    """

    def __init__(self, model_id: str, region: str = "us-east-1") -> None:
        self.model_id = model_id
        self.region = region
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3  # type: ignore[import]
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
            except ImportError:
                logger.warning("boto3 not available; Bedrock calls will be skipped.")
        return self._client

    def agent_turn(
        self,
        messages: list[dict],
        tools: dict,
        inference_config: dict | None = None,
    ) -> dict:
        """Call Bedrock Converse with toolConfig and message history.

        Returns the raw Bedrock response dict.
        Raises RuntimeError if mock-router is used (inject MockBedrockAgent in tests).
        """
        if self.model_id == "mock-router":
            raise RuntimeError(
                "mock-router cannot be used with agent_turn; inject MockBedrockAgent in tests"
            )
        client = self._get_client()
        if client is None:
            raise RuntimeError("Bedrock client unavailable")
        config = inference_config or {"maxTokens": 1024, "temperature": 0.0}
        response = client.converse(
            modelId=self.model_id,
            system=[{"text": AGENT_SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=tools,
            inferenceConfig=config,
        )
        return response

    def generate_plan_text(self, intent_domain: str, context: str) -> str | None:
        """Generate a natural-language plan summary using Bedrock Converse.

        Returns the generated text or None if Bedrock is unavailable.
        """
        if self.model_id == "mock-router":
            return None

        client = self._get_client()
        if client is None:
            return None

        system = (
            "You are a helpful personal assistant. "
            "Given a user intent and context, generate a concise, actionable plan summary. "
            "Be specific about what you found and what you propose. "
            "Do not add disclaimers or preamble."
        )
        user_message = f"Intent: {intent_domain}\n\nContext:\n{context}\n\nGenerate a plan summary."

        try:
            response = client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user_message}]}],
                inferenceConfig={"maxTokens": 512, "temperature": 0.3},
            )
            return (
                response.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
            )
        except Exception as exc:
            logger.warning("Bedrock generate_plan_text failed: %s", exc)
            return None


class BedrockGuardrail:
    """Applies a Bedrock guardrail to user input or model output.

    In mock mode (guardrail_id == "mock-guardrail") all content is passed through.
    """

    def __init__(self, guardrail_id: str, guardrail_version: str, region: str = "us-east-1") -> None:
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.region = region
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3  # type: ignore[import]
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
            except ImportError:
                logger.warning("boto3 not available; guardrail calls will be skipped.")
        return self._client

    def apply(self, text: str, source: str = "INPUT") -> tuple[bool, str]:
        """Apply the guardrail to ``text``.

        Args:
            text: The text to evaluate.
            source: ``"INPUT"`` for user messages, ``"OUTPUT"`` for model responses.

        Returns:
            A tuple of (passed: bool, safe_text: str).
            If the guardrail intervenes, ``passed`` is False and ``safe_text`` contains
            a sanitized message. If guardrails are not configured, returns (True, text).
        """
        if self.guardrail_id == "mock-guardrail":
            return True, text

        client = self._get_client()
        if client is None:
            return True, text

        try:
            response = client.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source=source,
                content=[{"text": {"text": text}}],
            )
            action = response.get("action", "NONE")
            if action == "GUARDRAIL_INTERVENED":
                outputs = response.get("outputs", [])
                safe_text = outputs[0].get("text", "I cannot help with that request.") if outputs else "I cannot help with that request."
                return False, safe_text
            return True, text
        except Exception as exc:
            logger.warning("Bedrock guardrail apply failed: %s", exc)
            return True, text

    # Alias so tests can patch either name
    check = apply


class MockBedrockAgent:
    """Test double for BedrockConverseRouter. Replays pre-programmed turn responses."""

    def __init__(self, turns: list[dict]) -> None:
        self._turns = iter(turns)
        self.calls: list[dict] = []  # captures (messages, tools) for each call

    def agent_turn(
        self,
        messages: list[dict],
        tools: dict,
        inference_config: dict | None = None,
    ) -> dict:
        self.calls.append({"messages": messages, "tools": tools})
        try:
            return next(self._turns)
        except StopIteration:
            raise RuntimeError(
                "MockBedrockAgent exhausted — more agent_turn calls than programmed turns"
            )
