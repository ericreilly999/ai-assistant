from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from assistant_app.config import AppConfig
from assistant_app.consent import build_action_proposal, validate_execute_request
from assistant_app.intent import classify_message, extract_grocery_items
from assistant_app.models import CalendarEvent, ExecuteResult, PlanResult
from assistant_app.registry import ProviderRegistry


class AssistantOrchestrator:
    def __init__(self, config: AppConfig, registry: ProviderRegistry) -> None:
        self.config = config
        self.registry = registry

    def plan(self, request_payload: dict) -> PlanResult:
        message = (request_payload.get("message") or "").strip()
        provider_names = request_payload.get("providers") or self.registry.providers()
        intent = classify_message(message)

        if intent.domain == "calendar" and intent.operation == "read":
            return self._calendar_plan(provider_names)
        if intent.domain == "meeting_prep":
            return self._meeting_prep_plan(provider_names)
        if intent.domain == "grocery":
            return self._grocery_plan(message, provider_names)
        if intent.domain == "travel":
            return self._travel_plan(provider_names)

        return PlanResult(
            intent=intent.domain,
            message="I understood the request but there is not a specialized workflow for it yet. The scaffold is ready for providers, planning, and consent-gated writes.",
            warnings=self._warnings(),
        )

    def execute(self, request_payload: dict) -> ExecuteResult:
        is_valid, validation_message = validate_execute_request(request_payload)
        if not is_valid:
            raise ValueError(validation_message)

        provider = request_payload.get("provider", "unknown")
        action_type = request_payload.get("action_type", "unknown")
        payload = request_payload.get("payload") or {}
        receipt = {
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "mode": "mock" if self.config.mock_provider_mode else "live",
            "proposal_id": request_payload.get("proposal_id", "unspecified"),
        }
        return ExecuteResult(
            message=f"Executed {action_type} against {provider} in {receipt['mode']} mode.",
            provider=provider,
            action_type=action_type,
            receipt=receipt,
            resource=payload,
        )

    def _calendar_plan(self, provider_names: Iterable[str]) -> PlanResult:
        events: list[CalendarEvent] = []
        sources: list[dict[str, str]] = []
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
        message = (
            "Tomorrow:\n"
            f"{schedule_text}\n\n"
            "You have two open windows:\n"
            "10:00-11:30\n"
            "12:30-15:00\n\n"
            "A gym session would fit in either window."
        )
        return PlanResult(intent="calendar", message=message, sources=sources, warnings=self._warnings())

    def _meeting_prep_plan(self, provider_names: Iterable[str]) -> PlanResult:
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

    def _warnings(self) -> list[str]:
        if self.config.mock_provider_mode:
            return ["Mock provider mode is enabled. Live SaaS calls are not executed in this scaffold."]
        return []