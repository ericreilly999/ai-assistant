from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable

from assistant_app.bedrock_client import BedrockConverseRouter, BedrockGuardrail
from assistant_app.config import AppConfig
from assistant_app.consent import build_action_proposal, validate_execute_request
from assistant_app.intent import IntentClassification, classify_message, extract_grocery_items
from assistant_app.models import CalendarEvent, ExecuteResult, PlanResult
from assistant_app.registry import ProviderRegistry

if TYPE_CHECKING:
    from assistant_app.live_service import LocalIntegrationService

logger = logging.getLogger(__name__)


class AssistantOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        registry: ProviderRegistry,
        live_service: "LocalIntegrationService | None" = None,
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

        # Apply input guardrail before processing
        passed, safe_message = self._guardrail.apply(message, source="INPUT")
        if not passed:
            return PlanResult(
                intent="blocked",
                message=safe_message,
                warnings=["Request blocked by content guardrail."],
            )
        message = safe_message

        # Prefer Bedrock-based intent classification; fall back to keyword classifier
        bedrock_classification = self._router.classify(message)
        if bedrock_classification:
            intent = IntentClassification(
                domain=bedrock_classification.get("domain", "general"),
                operation=bedrock_classification.get("operation", "read"),
                requires_confirmation=bedrock_classification.get("requires_confirmation", False),
            )
        else:
            intent = classify_message(message)

        logger.info(
            "plan.start request_id=%s intent=%s operation=%s providers=%s",
            request_id,
            intent.domain,
            intent.operation,
            provider_names,
        )

        try:
            if intent.domain == "calendar" and intent.operation == "read":
                result = self._calendar_plan(provider_names)
            elif intent.domain == "meeting_prep":
                result = self._meeting_prep_plan(provider_names)
            elif intent.domain == "grocery":
                result = self._grocery_plan(message, provider_names)
            elif intent.domain == "travel":
                result = self._travel_plan(provider_names)
            elif intent.domain == "tasks":
                result = self._tasks_plan(message, provider_names)
            else:
                result = PlanResult(
                    intent=intent.domain,
                    message=(
                        "I can help you with calendars, tasks, grocery lists, travel planning, "
                        "and meeting preparation. Could you tell me more about what you need?"
                    ),
                    warnings=self._warnings(),
                )
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.info("plan.done request_id=%s intent=%s latency_ms=%d", request_id, intent.domain, latency_ms)

        return result

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

        if provider == "google_calendar":
            if action_type == "create_calendar_event":
                result = self._live.create_google_calendar_event(payload)
                return result.get("event", payload)

        if provider == "microsoft_calendar":
            if action_type == "create_calendar_event":
                result = self._live.create_microsoft_calendar_event(payload)
                return result.get("event", payload)

        raise ValueError(f"No live handler for provider={provider} action_type={action_type}.")

    # -------------------------------------------------------------------------
    # Plan methods
    # -------------------------------------------------------------------------

    def _calendar_plan(self, provider_names: Iterable[str]) -> PlanResult:
        events: list[CalendarEvent] = []
        sources: list[dict[str, str]] = []

        if not self.config.mock_provider_mode and self._live is not None:
            return self._live_calendar_plan(provider_names)

        for provider_name in provider_names:
            if provider_name not in {"google_calendar", "microsoft_calendar"}:
                continue
            adapter = self.registry.get(provider_name)
            provider_events = adapter.list_mock_events()
            events.extend(provider_events)
            sources.append({"provider": provider_name, "type": "calendar"})

        events.sort(key=lambda item: item.start)
        schedule_lines = [self._format_event_line(event) for event in events]
        schedule_text = "\n".join(schedule_lines) if schedule_lines else "No events found."
        open_windows = self._compute_open_windows(events)
        window_text = "\n".join(open_windows) if open_windows else "No open windows found."
        message = (
            "Tomorrow:\n"
            f"{schedule_text}\n\n"
            "Open windows:\n"
            f"{window_text}\n\n"
            "A gym session would fit in either window."
        )
        return PlanResult(intent="calendar", message=message, sources=sources, warnings=self._warnings())

    def _live_calendar_plan(self, provider_names: Iterable[str]) -> PlanResult:
        assert self._live is not None
        events: list[CalendarEvent] = []
        sources: list[dict[str, str]] = []
        provider_list = list(provider_names)

        if "google_calendar" in provider_list:
            try:
                from datetime import timedelta

                tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_end = tomorrow.replace(hour=23, minute=59, second=59)
                raw = self._live.list_google_calendar_events(
                    tomorrow.isoformat(), day_end.isoformat()
                )
                adapter = self.registry.get("google_calendar")
                for item in raw.get("events", []):
                    try:
                        events.append(adapter.normalize_event(item))
                    except Exception:
                        pass
                sources.append({"provider": "google_calendar", "type": "calendar"})
            except Exception as exc:
                logger.warning("google_calendar live fetch failed: %s", exc)

        if "microsoft_calendar" in provider_list:
            try:
                from datetime import timedelta

                tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_end = tomorrow.replace(hour=23, minute=59, second=59)
                raw = self._live.list_microsoft_calendar_events(
                    tomorrow.isoformat(), day_end.isoformat()
                )
                adapter = self.registry.get("microsoft_calendar")
                for item in raw.get("events", []):
                    try:
                        events.append(adapter.normalize_event(item))
                    except Exception:
                        pass
                sources.append({"provider": "microsoft_calendar", "type": "calendar"})
            except Exception as exc:
                logger.warning("microsoft_calendar live fetch failed: %s", exc)

        events.sort(key=lambda item: item.start)
        schedule_lines = [self._format_event_line(event) for event in events]
        schedule_text = "\n".join(schedule_lines) if schedule_lines else "No events found."
        open_windows = self._compute_open_windows(events)
        window_text = "\n".join(open_windows) if open_windows else "No open windows found."
        message = (
            "Tomorrow:\n"
            f"{schedule_text}\n\n"
            "Open windows:\n"
            f"{window_text}"
        )
        return PlanResult(intent="calendar", message=message, sources=sources, warnings=self._warnings())

    def _meeting_prep_plan(self, provider_names: Iterable[str]) -> PlanResult:
        if not self.config.mock_provider_mode and self._live is not None:
            return self._live_meeting_prep_plan(provider_names)
        return self._mock_meeting_prep_plan(provider_names)

    def _mock_meeting_prep_plan(self, provider_names: Iterable[str]) -> PlanResult:
        sources: list[dict[str, str]] = []
        documents = []
        if "google_drive" in provider_names:
            documents = self.registry.get("google_drive").list_mock_documents()
            sources.append({"provider": "google_drive", "type": "documents"})

        if any(provider in provider_names for provider in ("google_calendar", "microsoft_calendar")):
            sources.append({"provider": "calendar", "type": "calendar_context"})

        document_titles = ", ".join(document.title for document in documents) if documents else "No linked docs"
        message = (
            "Architecture Review - 2:00 PM\n\n"
            "Agenda highlights:\n"
            "- migration to ECS\n"
            "- load balancing strategy\n"
            "- observability rollout\n\n"
            "Key risks:\n"
            "- container cold starts\n"
            "- IAM permissions complexity\n\n"
            f"Referenced documents: {document_titles}"
        )
        return PlanResult(intent="meeting_prep", message=message, sources=sources, warnings=self._warnings())

    def _live_meeting_prep_plan(self, provider_names: Iterable[str]) -> PlanResult:
        """Meeting prep using real Drive documents and calendar context."""
        assert self._live is not None
        provider_list = list(provider_names)
        sources: list[dict[str, str]] = []
        document_titles: list[str] = []
        document_summaries: list[str] = []

        if "google_drive" in provider_list:
            try:
                raw = self._live.list_google_drive_documents(None)
                docs = raw.get("documents", [])
                sources.append({"provider": "google_drive", "type": "documents"})
                for doc in docs[:5]:
                    title = doc.get("title", "Untitled")
                    document_titles.append(title)
                    try:
                        export = self._live.export_google_drive_document(doc["id"], "text/plain")
                        snippet = (export.get("content") or "")[:500].strip()
                        if snippet:
                            document_summaries.append(f"**{title}**: {snippet[:200]}…")
                    except Exception:
                        document_summaries.append(f"**{title}**: (export unavailable)")
            except Exception as exc:
                logger.warning("google_drive live fetch failed: %s", exc)

        if any(p in provider_list for p in ("google_calendar", "microsoft_calendar")):
            sources.append({"provider": "calendar", "type": "calendar_context"})

        titles_text = ", ".join(document_titles) if document_titles else "No linked documents found"
        summaries_text = "\n".join(document_summaries) if document_summaries else ""

        message = (
            "Meeting Preparation\n\n"
            f"Referenced documents: {titles_text}\n"
        )
        if summaries_text:
            message += f"\nDocument excerpts:\n{summaries_text}\n"
        message += (
            "\nReview the linked documents above for full context before your meeting."
        )

        return PlanResult(intent="meeting_prep", message=message, sources=sources, warnings=self._warnings())

    def _grocery_plan(self, message: str, provider_names: Iterable[str]) -> PlanResult:
        task_provider = self._preferred_task_provider(provider_names)
        items = extract_grocery_items(message)
        payload = {"list_name": "Groceries", "items": items}
        proposal = build_action_proposal(
            provider=task_provider,
            action_type="upsert_grocery_items",
            resource_type="task_list",
            payload=payload,
            summary=f"Add {len(items)} item(s) to the Groceries list in {task_provider}.",
            ttl_minutes=self.config.proposal_ttl_minutes,
            message=message,
        )
        return PlanResult(
            intent="grocery",
            message=f"I prepared a grocery list proposal with {len(items)} item(s). Review and approve it before any write occurs.",
            proposals=[proposal],
            sources=[{"provider": task_provider, "type": "task_list"}],
            warnings=self._warnings(),
        )

    def _travel_plan(self, provider_names: Iterable[str]) -> PlanResult:
        calendar_provider = self._preferred_calendar_provider(provider_names)
        payload = {
            "title": "Weekend Trip Placeholder",
            "start": "2026-05-10T09:00:00-04:00",
            "end": "2026-05-12T18:00:00-04:00",
            "reminder_minutes": 120,
        }
        proposal = build_action_proposal(
            provider=calendar_provider,
            action_type="create_calendar_event",
            resource_type="calendar_event",
            payload=payload,
            summary="Create a weekend-trip placeholder hold on the calendar.",
            ttl_minutes=self.config.proposal_ttl_minutes,
        )
        message = (
            "Best weekend: May 10-12\n\n"
            "Draft itinerary:\n"
            "- Friday: travel to Miami\n"
            "- Saturday: beach and dinner\n"
            "- Sunday: brunch and return\n\n"
            "I also prepared a calendar-hold proposal for review."
        )
        return PlanResult(
            intent="travel",
            message=message,
            proposals=[proposal],
            sources=[{"provider": calendar_provider, "type": "calendar"}],
            warnings=self._warnings(),
        )

    def _tasks_plan(self, message: str, provider_names: Iterable[str]) -> PlanResult:
        task_provider = self._preferred_task_provider(provider_names)
        normalized = message.lower()

        if any(token in normalized for token in ("complete", "finish", "done", "check off")):
            action_type = "complete_task"
            summary = "Mark a task as complete."
            payload = {"list_id": "", "task_id": "", "note": message}
        elif any(token in normalized for token in ("update", "rename", "change", "edit")):
            action_type = "update_task"
            summary = "Update a task."
            payload = {"list_id": "", "task_id": "", "updates": {}, "note": message}
        else:
            action_type = "update_task"
            summary = "Update or complete a task."
            payload = {"list_id": "", "task_id": "", "updates": {}, "note": message}

        proposal = build_action_proposal(
            provider=task_provider,
            action_type=action_type,
            resource_type="task",
            payload=payload,
            summary=summary,
            ttl_minutes=self.config.proposal_ttl_minutes,
            message=message,
        )
        return PlanResult(
            intent="tasks",
            message=f"I prepared a task-update proposal. Review and approve it before any write occurs.",
            proposals=[proposal],
            sources=[{"provider": task_provider, "type": "task_list"}],
            warnings=self._warnings(),
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _preferred_task_provider(self, provider_names: Iterable[str]) -> str:
        for provider_name in provider_names:
            if provider_name in {"google_tasks", "microsoft_todo"}:
                return provider_name
        return "google_tasks"

    def _preferred_calendar_provider(self, provider_names: Iterable[str]) -> str:
        for provider_name in provider_names:
            if provider_name in {"google_calendar", "microsoft_calendar"}:
                return provider_name
        return "google_calendar"

    def _format_event_line(self, event: CalendarEvent) -> str:
        start_time = event.start[11:16] if len(event.start) >= 16 else event.start
        end_time = event.end[11:16] if len(event.end) >= 16 else event.end
        return f"{start_time}-{end_time} {event.title}"

    def _compute_open_windows(self, events: list[CalendarEvent]) -> list[str]:
        """Return a simple list of open time windows between events (09:00-18:00 range)."""
        busy: list[tuple[str, str]] = [(e.start[11:16], e.end[11:16]) for e in events
                                        if len(e.start) >= 16 and len(e.end) >= 16]
        busy.sort()

        day_start = "09:00"
        day_end = "18:00"
        windows: list[str] = []
        current = day_start

        for start_t, end_t in busy:
            if current < start_t:
                windows.append(f"{current}-{start_t}")
            if end_t > current:
                current = end_t

        if current < day_end:
            windows.append(f"{current}-{day_end}")

        return windows

    def _warnings(self) -> list[str]:
        if self.config.mock_provider_mode:
            return ["Mock provider mode is enabled. Live SaaS calls are not executed in this scaffold."]
        return []
