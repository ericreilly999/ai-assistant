from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from assistant_app.bedrock_client import BedrockConverseRouter, BedrockGuardrail
from assistant_app.config import AppConfig
from assistant_app.consent import validate_execute_request
from assistant_app.models import ExecuteResult, PlanResult, ToolInputError
from assistant_app.registry import ProviderRegistry
from assistant_app.tool_definitions import build_tool_config
from assistant_app.tool_handlers import ToolContext, dispatch

if TYPE_CHECKING:
    from assistant_app.live_service import LocalIntegrationService

logger = logging.getLogger(__name__)

MAX_TURNS = 5


class AssistantOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        registry: ProviderRegistry,
        live_service: LocalIntegrationService | None = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self._live = live_service
        self._router = BedrockConverseRouter(
            model_id=config.bedrock_router_model_id,
            region=getattr(config, "aws_region", "us-east-1"),
        )
        self._guardrail = BedrockGuardrail(
            guardrail_id=config.bedrock_guardrail_id,
            guardrail_version=config.bedrock_guardrail_version,
            region=getattr(config, "aws_region", "us-east-1"),
        )

    def plan(self, request_payload: dict) -> PlanResult:
        request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()
        message = (request_payload.get("message") or "").strip()
        provider_names = request_payload.get("providers") or self.registry.providers()
        history = request_payload.get("history") or []

        # Apply input guardrail
        passed, safe_message = self._guardrail.check(message, source="INPUT")
        if not passed:
            return PlanResult(
                intent="blocked",
                message=safe_message,
                warnings=["Request blocked by content guardrail."],
            )
        message = safe_message

        # Truncate history to last 10 turns
        if len(history) > 10:
            dropped = len(history) - 10
            logger.debug(
                "plan.history_truncated request_id=%s dropped=%d", request_id, dropped
            )
            history = history[-10:]

        # Build initial messages list
        messages = []
        for turn in history:
            messages.append({"role": turn["role"], "content": [{"text": turn["content"]}]})
        messages.append({"role": "user", "content": [{"text": message}]})

        tools = build_tool_config(list(provider_names))
        ctx = ToolContext(
            config=self.config,
            registry=self.registry,
            live_service=self._live,
            messages=messages,
            proposals_accumulator=[],
            sources_accumulator=[],
        )

        consecutive_errors = 0
        turn_count = 0

        logger.info(
            "plan.start request_id=%s providers=%s history_turns=%d",
            request_id,
            list(provider_names),
            len(history),
        )

        try:
            while True:
                turn_count += 1
                if turn_count > getattr(self.config, "max_agent_turns", MAX_TURNS):
                    logger.error(
                        "agent.turn_limit_exceeded request_id=%s turn_count=%d",
                        request_id,
                        turn_count - 1,
                    )
                    return PlanResult(
                        intent="error",
                        message=(
                            "I was unable to complete your request — the agent loop exceeded "
                            "the turn limit (maximum number of steps). "
                            "Please try rephrasing your request."
                        ),
                        proposals=ctx.proposals_accumulator,
                        warnings=["Agent turn limit exceeded."],
                    )

                response = self._router.agent_turn(
                    messages, tools, {"maxTokens": 1024, "temperature": 0.0}
                )

                # Log token usage
                usage = response.get("usage", {})
                logger.info(
                    "bedrock.token_usage request_id=%s turn=%d input_tokens=%d "
                    "output_tokens=%d total_tokens=%d",
                    request_id,
                    turn_count,
                    usage.get("inputTokens", 0),
                    usage.get("outputTokens", 0),
                    usage.get("inputTokens", 0) + usage.get("outputTokens", 0),
                )

                stop_reason = response.get("stopReason", "end_turn")
                output_message = response.get("output", {}).get("message", {})

                if stop_reason == "end_turn":
                    # Extract text response
                    text = ""
                    for block in output_message.get("content", []):
                        if "text" in block:
                            text = block["text"]
                            break

                    # Apply output guardrail
                    passed, safe_text = self._guardrail.check(text, source="OUTPUT")
                    if not passed:
                        return PlanResult(
                            intent="blocked",
                            message=safe_text,
                            warnings=["Response blocked by content guardrail."],
                        )

                    return PlanResult(
                        intent="agent",
                        message=safe_text,
                        proposals=ctx.proposals_accumulator,
                        sources=ctx.sources_accumulator,
                        warnings=self._warnings(),
                    )

                elif stop_reason == "tool_use":
                    # Append assistant message
                    messages.append(output_message)
                    ctx.messages = messages

                    # Process all tool use blocks
                    tool_results = []
                    for block in output_message.get("content", []):
                        if "toolUse" not in block:
                            continue
                        tool_use = block["toolUse"]
                        tool_use_id = tool_use["toolUseId"]
                        tool_name = tool_use["name"]
                        tool_input = tool_use.get("input", {})

                        try:
                            result = dispatch(tool_name, tool_input, ctx)
                            is_error = result.get("isError", False)
                            if is_error:
                                consecutive_errors += 1
                                tool_results.append({
                                    "toolResult": {
                                        "toolUseId": tool_use_id,
                                        "content": [{"text": result.get("content", str(result))}],
                                        "status": "error",
                                    }
                                })
                            else:
                                consecutive_errors = 0
                                tool_results.append({
                                    "toolResult": {
                                        "toolUseId": tool_use_id,
                                        "content": [{"json": result}],
                                    }
                                })
                        except ToolInputError as e:
                            consecutive_errors += 1
                            logger.warning(
                                "tool.input_error request_id=%s tool=%s field=%s",
                                request_id,
                                tool_name,
                                e.field,
                            )
                            tool_results.append({
                                "toolResult": {
                                    "toolUseId": tool_use_id,
                                    "content": [{"text": str(e)}],
                                    "status": "error",
                                }
                            })
                        except Exception as e:
                            consecutive_errors += 1
                            logger.warning(
                                "tool.execution_error request_id=%s tool=%s error=%s",
                                request_id,
                                tool_name,
                                e,
                            )
                            tool_results.append({
                                "toolResult": {
                                    "toolUseId": tool_use_id,
                                    "content": [{"text": f"Tool execution failed: {e}"}],
                                    "status": "error",
                                }
                            })

                    if consecutive_errors >= 3:
                        return PlanResult(
                            intent="error",
                            message="I encountered repeated errors processing your request. Please try again.",
                            proposals=ctx.proposals_accumulator,
                            warnings=["Repeated tool errors."],
                        )

                    # Append tool results as user message
                    messages.append({"role": "user", "content": tool_results})
                    ctx.messages = messages

                else:
                    logger.warning(
                        "agent.unexpected_stop_reason request_id=%s stop_reason=%s",
                        request_id,
                        stop_reason,
                    )
                    return PlanResult(
                        intent="error",
                        message="I encountered an unexpected response. Please try again.",
                        proposals=ctx.proposals_accumulator,
                        warnings=[f"Unexpected stop reason: {stop_reason}"],
                    )

        except Exception as e:
            logger.error("agent.bedrock_error request_id=%s error=%s", request_id, e)
            return PlanResult(
                intent="error",
                message="I'm temporarily unavailable. Please try again in a moment.",
                warnings=["Bedrock unavailable."],
            )
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "plan.done request_id=%s latency_ms=%d turns=%d",
                request_id,
                latency_ms,
                turn_count,
            )

    def execute(self, request_payload: dict) -> ExecuteResult:
        request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        is_valid, validation_message = validate_execute_request(request_payload)
        if not is_valid:
            raise ValueError(validation_message)

        provider = request_payload.get("provider", "unknown")
        action_type = request_payload.get("action_type", "unknown")
        payload = request_payload.get("payload") or {}

        logger.info(
            "execute.start request_id=%s provider=%s action_type=%s",
            request_id,
            provider,
            action_type,
        )

        mode = "mock" if self.config.mock_provider_mode else "live"

        try:
            if not self.config.mock_provider_mode and self._live is not None:
                resource = self._execute_live(provider, action_type, payload)
            else:
                resource = payload

            receipt = {
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "proposal_id": request_payload.get("proposal_id", "unspecified"),
            }
            result = ExecuteResult(
                message=f"Executed {action_type} against {provider} in {mode} mode.",
                provider=provider,
                action_type=action_type,
                receipt=receipt,
                resource=resource,
            )
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "execute.done request_id=%s provider=%s action_type=%s mode=%s latency_ms=%d",
                request_id,
                provider,
                action_type,
                mode,
                latency_ms,
            )

        return result

    def _execute_live(self, provider: str, action_type: str, payload: dict) -> dict:
        """Dispatch a live write action to the appropriate provider adapter."""
        if self._live is None:
            raise ValueError("Live service is not available for execution.")

        if provider == "google_tasks":
            if action_type == "upsert_grocery_items":
                self._live.add_google_grocery_items(payload)
                return payload
            if action_type == "update_task":
                list_id = payload["list_id"]
                task_id = payload["task_id"]
                updates = payload.get("updates", {})
                return self._live.update_google_task(list_id, task_id, updates)
            if action_type == "complete_task":
                list_id = payload["list_id"]
                task_id = payload["task_id"]
                return self._live.complete_google_task(list_id, task_id)

        if provider == "microsoft_todo":
            if action_type == "upsert_grocery_items":
                self._live.add_microsoft_grocery_items(payload)
                return payload
            if action_type == "update_task":
                list_id = payload["list_id"]
                task_id = payload["task_id"]
                updates = payload.get("updates", {})
                return self._live.update_microsoft_task(list_id, task_id, updates)
            if action_type == "complete_task":
                list_id = payload["list_id"]
                task_id = payload["task_id"]
                return self._live.complete_microsoft_task(list_id, task_id)

        if provider == "google_calendar" and action_type == "create_calendar_event":
            result = self._live.create_google_calendar_event(payload)
            return result.get("event", payload)

        if provider == "microsoft_calendar" and action_type == "create_calendar_event":
            result = self._live.create_microsoft_calendar_event(payload)
            return result.get("event", payload)

        raise ValueError(f"No live handler for provider={provider} action_type={action_type}.")

    # -------------------------------------------------------------------------
    # Helpers (still used by execute() path)
    # -------------------------------------------------------------------------

    def _preferred_task_provider(self, provider_names) -> str:
        for provider_name in provider_names:
            if provider_name in {"google_tasks", "microsoft_todo"}:
                return provider_name
        return "google_tasks"

    def _preferred_calendar_provider(self, provider_names) -> str:
        for provider_name in provider_names:
            if provider_name in {"google_calendar", "microsoft_calendar"}:
                return provider_name
        return "google_calendar"

    def _warnings(self) -> list[str]:
        if self.config.mock_provider_mode:
            return ["Mock provider mode is enabled. Live SaaS calls are not executed in this scaffold."]
        return []
