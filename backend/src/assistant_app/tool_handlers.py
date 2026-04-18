"""Tool handlers for the Phase 13 LLM Tool Use Orchestrator.

Each handler function executes one tool, either in mock mode (returning static
test data) or live mode (calling provider APIs via live_service).

All mock data is defined as module-level constants for determinism.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from assistant_app.config import AppConfig
from assistant_app.consent import build_action_proposal
from assistant_app.models import ToolInputError
from assistant_app.registry import ProviderRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data constants
# ---------------------------------------------------------------------------

# MOCK: deterministic calendar events for tomorrow (2026-04-19)
MOCK_CALENDAR_EVENTS = [
    {
        "id": "evt-001",
        "title": "Team Standup",
        "start": "2026-04-19T09:00:00-04:00",
        "end": "2026-04-19T09:30:00-04:00",
        "location": "",
        "source": "google_calendar",
    },
    {
        "id": "evt-002",
        "title": "Architecture Review",
        "start": "2026-04-19T14:00:00-04:00",
        "end": "2026-04-19T15:00:00-04:00",
        "location": "Zoom",
        "source": "google_calendar",
    },
    {
        "id": "evt-003",
        "title": "1:1 with Manager",
        "start": "2026-04-19T16:00:00-04:00",
        "end": "2026-04-19T16:30:00-04:00",
        "location": "",
        "source": "google_calendar",
    },
]

# MOCK: task lists
MOCK_TASK_LISTS = [
    {"id": "list-001", "name": "My Tasks"},
    {"id": "list-002", "name": "Work"},
    {"id": "list-003", "name": "Groceries"},
]

# MOCK: tasks per list
MOCK_TASKS: dict[str, list[dict]] = {
    "list-001": [
        {
            "id": "task-001",
            "title": "Review contracts",
            "status": "needsAction",
            "due": "2026-04-20",
            "list_name": "My Tasks",
            "source": "google_tasks",
        },
        {
            "id": "task-002",
            "title": "Call dentist",
            "status": "needsAction",
            "due": None,
            "list_name": "My Tasks",
            "source": "google_tasks",
        },
        {
            "id": "task-003",
            "title": "Buy groceries",
            "status": "needsAction",
            "due": "2026-04-19",
            "list_name": "My Tasks",
            "source": "google_tasks",
        },
        {
            "id": "task-004",
            "title": "Submit expense report",
            "status": "completed",
            "due": None,
            "list_name": "My Tasks",
            "source": "google_tasks",
        },
    ],
    "list-002": [],
    "list-003": [],
}

# MOCK: documents
MOCK_DOCUMENTS = [
    {
        "id": "doc-001",
        "title": "Architecture Review Deck",
        "web_view_link": "https://docs.google.com/doc-001",
        "mime_type": "application/vnd.google-apps.presentation",
    },
    {
        "id": "doc-002",
        "title": "Q2 Roadmap",
        "web_view_link": "https://docs.google.com/doc-002",
        "mime_type": "application/vnd.google-apps.document",
    },
]

# MOCK: grocery lists
MOCK_GROCERY_LISTS = [
    {
        "list_id": "list-003",
        "list_name": "Groceries",
        "items": [
            {"id": "item-001", "title": "Milk", "status": "needsAction"},
            {"id": "item-002", "title": "Eggs", "status": "needsAction"},
            {"id": "item-003", "title": "Bread", "status": "needsAction"},
        ],
    }
]


# ---------------------------------------------------------------------------
# ToolContext dataclass
# ---------------------------------------------------------------------------


@dataclass
class ToolContext:
    """Context passed to every tool handler."""

    config: AppConfig
    registry: ProviderRegistry
    live_service: Any  # LocalIntegrationService | None
    messages: list[dict]
    proposals_accumulator: list
    sources_accumulator: list


# ---------------------------------------------------------------------------
# ID validation helper
# ---------------------------------------------------------------------------


def _extract_prior_task_ids(messages: list[dict]) -> set[str]:
    """Scan messages for get_tasks toolResult blocks and extract task IDs."""
    task_ids: set[str] = set()
    for msg in messages:
        if msg.get("role") != "user":
            continue
        for content_block in msg.get("content", []):
            tool_result = content_block.get("toolResult", {})
            # Extract task IDs from any toolResult that contains a tasks list
            for result_content in tool_result.get("content", []):
                data = result_content.get("json", {})
                for task in data.get("tasks", []):
                    if task.get("id"):
                        task_ids.add(task["id"])
    return task_ids


# ---------------------------------------------------------------------------
# Read tool handlers
# ---------------------------------------------------------------------------


def handle_get_calendar_events(tool_input: dict, ctx: ToolContext) -> dict:
    """Fetch calendar events for a date range.

    Validates required start and end fields. In mock mode returns MOCK_CALENDAR_EVENTS.
    """
    # Validate required fields
    if "start" not in tool_input or tool_input["start"] is None:
        raise ToolInputError("get_calendar_events", "start", "start is required")
    if "end" not in tool_input or tool_input["end"] is None:
        raise ToolInputError("get_calendar_events", "end", "end is required")

    if ctx.config.mock_provider_mode:  # MOCK
        events = MOCK_CALENDAR_EVENTS[:20]
        return {
            "events": events,
            "provider": "google_calendar",
            "count": len(events),
            "truncated": False,
        }

    # Live path
    provider = tool_input.get("provider", "google_calendar")
    start = tool_input["start"]
    end = tool_input["end"]
    try:
        if provider == "microsoft_calendar":
            raw = ctx.live_service.list_microsoft_calendar_events(start, end)
        else:
            raw = ctx.live_service.list_google_calendar_events(start, end)
        events = raw.get("events", [])[:20]
        truncated = len(raw.get("events", [])) > 20
        return {
            "events": events,
            "provider": provider,
            "count": len(events),
            "truncated": truncated,
        }
    except Exception as exc:
        return {
            "isError": True,
            "content": f"Unable to fetch data from {provider}: {exc}. Check that {provider} is connected.",
        }


def handle_get_task_lists(tool_input: dict, ctx: ToolContext) -> dict:
    """Fetch all task list names and IDs."""
    if ctx.config.mock_provider_mode:  # MOCK
        return {
            "task_lists": MOCK_TASK_LISTS,
            "provider": "google_tasks",
            "count": len(MOCK_TASK_LISTS),
        }

    # Live path
    provider = tool_input.get("provider", "google_tasks")
    try:
        if provider == "microsoft_todo":
            raw = ctx.live_service.list_microsoft_tasklists()
        else:
            raw = ctx.live_service.list_google_tasklists()
        task_lists = raw.get("task_lists", raw.get("lists", []))
        return {
            "task_lists": task_lists,
            "provider": provider,
            "count": len(task_lists),
        }
    except Exception as exc:
        return {
            "isError": True,
            "content": f"Unable to fetch data from {provider}: {exc}. Check that {provider} is connected.",
        }


def handle_get_tasks(tool_input: dict, ctx: ToolContext) -> dict:
    """Fetch tasks within a specific task list."""
    if "list_id" not in tool_input or tool_input["list_id"] is None:
        raise ToolInputError("get_tasks", "list_id", "list_id is required")

    list_id: str = tool_input["list_id"]

    if ctx.config.mock_provider_mode:  # MOCK
        tasks = MOCK_TASKS.get(list_id, [])
        capped = tasks[:50]
        return {
            "tasks": capped,
            "list_id": list_id,
            "provider": "google_tasks",
            "count": len(capped),
            "truncated": len(tasks) > 50,
        }

    # Live path
    provider = tool_input.get("provider", "google_tasks")
    try:
        if provider == "microsoft_todo":
            raw = ctx.live_service.list_microsoft_tasks(list_id, None)
        else:
            raw = ctx.live_service.list_google_tasks(list_id, None)
        tasks = raw.get("tasks", raw.get("items", []))
        capped = tasks[:50]
        return {
            "tasks": capped,
            "list_id": list_id,
            "provider": provider,
            "count": len(capped),
            "truncated": len(tasks) > 50,
        }
    except Exception as exc:
        return {
            "isError": True,
            "content": f"Unable to fetch data from {provider}: {exc}. Check that {provider} is connected.",
        }


def handle_get_meeting_documents(tool_input: dict, ctx: ToolContext) -> dict:
    """Fetch Google Drive documents related to an upcoming meeting."""
    if ctx.config.mock_provider_mode:  # MOCK
        return {
            "documents": MOCK_DOCUMENTS,
            "provider": "google_drive",
            "count": len(MOCK_DOCUMENTS),
        }

    # Live path
    keyword = tool_input.get("keyword")
    try:
        raw = ctx.live_service.list_google_drive_documents(keyword)
        documents = raw.get("documents", [])[:10]
        return {
            "documents": documents,
            "provider": "google_drive",
            "count": len(documents),
        }
    except Exception as exc:
        return {
            "isError": True,
            "content": f"Unable to fetch data from google_drive: {exc}. Check that google_drive is connected.",
        }


def handle_get_grocery_lists(tool_input: dict, ctx: ToolContext) -> dict:
    """Fetch existing grocery/shopping lists and their current items."""
    if ctx.config.mock_provider_mode:  # MOCK
        return {
            "grocery_lists": MOCK_GROCERY_LISTS,
            "provider": "google_tasks",
            "count": len(MOCK_GROCERY_LISTS),
        }

    # Live path
    provider = tool_input.get("provider", "google_tasks")
    try:
        if provider == "microsoft_todo":
            raw = ctx.live_service.list_microsoft_tasklists()
        else:
            raw = ctx.live_service.list_google_tasklists()
        # Filter for grocery-like lists
        all_lists = raw.get("task_lists", raw.get("lists", []))
        grocery_lists = []
        for lst in all_lists:
            name = lst.get("name", "")
            if "grocer" in name.lower() or "shopping" in name.lower():
                grocery_lists.append({
                    "list_id": lst.get("id", ""),
                    "list_name": name,
                    "items": [],
                })
        return {
            "grocery_lists": grocery_lists,
            "provider": provider,
            "count": len(grocery_lists),
        }
    except Exception as exc:
        return {
            "isError": True,
            "content": f"Unable to fetch data from {provider}: {exc}. Check that {provider} is connected.",
        }


# ---------------------------------------------------------------------------
# Write-proposal tool handlers
# ---------------------------------------------------------------------------


def handle_propose_calendar_event(tool_input: dict, ctx: ToolContext) -> dict:
    """Propose creating a new calendar event."""
    # Validate required fields
    if "title" not in tool_input or tool_input["title"] is None:
        raise ToolInputError("propose_calendar_event", "title", "title is required")
    if "start" not in tool_input or tool_input["start"] is None:
        raise ToolInputError("propose_calendar_event", "start", "start is required")
    if "end" not in tool_input or tool_input["end"] is None:
        raise ToolInputError("propose_calendar_event", "end", "end is required")

    provider = tool_input.get("provider") or (
        ctx.config and _preferred_calendar_provider(ctx) or "google_calendar"
    )

    payload: dict[str, Any] = {
        "title": tool_input["title"],
        "start": tool_input["start"],
        "end": tool_input["end"],
    }
    if tool_input.get("location"):
        payload["location"] = tool_input["location"]
    if tool_input.get("notes"):
        payload["notes"] = tool_input["notes"]
    if tool_input.get("reminder_minutes") is not None:
        payload["reminder_minutes"] = tool_input["reminder_minutes"]

    summary = f"Create calendar event: '{tool_input['title']}' from {tool_input['start']} to {tool_input['end']}."

    proposal = build_action_proposal(
        provider=provider,
        action_type="create_calendar_event",
        resource_type="calendar_event",
        payload=payload,
        summary=summary,
        ttl_minutes=ctx.config.proposal_ttl_minutes,
    )
    ctx.proposals_accumulator.append(proposal)

    return {
        "proposal_created": True,
        "proposal_id": proposal.proposal_id,
        "summary": proposal.summary,
        "action_type": "create_calendar_event",
        "provider": provider,
        "risk_level": proposal.risk_level,
    }


def handle_propose_task_update(tool_input: dict, ctx: ToolContext) -> dict:
    """Propose updating a task's title, due date, or notes."""
    # Validate required fields
    if "list_id" not in tool_input or tool_input["list_id"] is None:
        raise ToolInputError("propose_task_update", "list_id", "list_id is required")
    if "task_id" not in tool_input or tool_input["task_id"] is None:
        raise ToolInputError("propose_task_update", "task_id", "task_id is required")
    if "updates" not in tool_input or tool_input["updates"] is None:
        raise ToolInputError("propose_task_update", "updates", "updates is required")

    task_id: str = tool_input["task_id"]

    # ID validation: task_id must come from a prior get_tasks result
    prior_task_ids = _extract_prior_task_ids(ctx.messages)
    if task_id not in prior_task_ids:
        logger.warning(
            "hallucinated_id_blocked tool=propose_task_update task_id=%s", task_id
        )
        return {
            "isError": True,
            "content": (
                "list_id and task_id must come from a get_tasks result in this conversation. "
                "Please call get_task_lists then get_tasks first."
            ),
        }

    provider = tool_input.get("provider") or _preferred_task_provider(ctx)

    payload: dict[str, Any] = {
        "list_id": tool_input["list_id"],
        "task_id": task_id,
        "updates": tool_input["updates"],
    }

    summary = f"Update task '{task_id}' in list '{tool_input['list_id']}'."

    proposal = build_action_proposal(
        provider=provider,
        action_type="update_task",
        resource_type="task",
        payload=payload,
        summary=summary,
        ttl_minutes=ctx.config.proposal_ttl_minutes,
    )
    ctx.proposals_accumulator.append(proposal)

    return {
        "proposal_created": True,
        "proposal_id": proposal.proposal_id,
        "summary": proposal.summary,
        "action_type": "update_task",
        "provider": provider,
        "risk_level": proposal.risk_level,
    }


def handle_propose_task_complete(tool_input: dict, ctx: ToolContext) -> dict:
    """Propose marking a task as complete."""
    # Validate required fields
    if "list_id" not in tool_input or tool_input["list_id"] is None:
        raise ToolInputError("propose_task_complete", "list_id", "list_id is required")
    if "task_id" not in tool_input or tool_input["task_id"] is None:
        raise ToolInputError("propose_task_complete", "task_id", "task_id is required")

    task_id: str = tool_input["task_id"]

    # ID validation: task_id must come from a prior get_tasks result
    prior_task_ids = _extract_prior_task_ids(ctx.messages)
    if task_id not in prior_task_ids:
        logger.warning(
            "hallucinated_id_blocked tool=propose_task_complete task_id=%s", task_id
        )
        return {
            "isError": True,
            "content": (
                "list_id and task_id must come from a get_tasks result in this conversation. "
                "Please call get_task_lists then get_tasks first."
            ),
        }

    provider = tool_input.get("provider") or _preferred_task_provider(ctx)

    payload: dict[str, Any] = {
        "list_id": tool_input["list_id"],
        "task_id": task_id,
    }

    summary = f"Mark task '{task_id}' in list '{tool_input['list_id']}' as complete."

    proposal = build_action_proposal(
        provider=provider,
        action_type="complete_task",
        resource_type="task",
        payload=payload,
        summary=summary,
        ttl_minutes=ctx.config.proposal_ttl_minutes,
    )
    ctx.proposals_accumulator.append(proposal)

    return {
        "proposal_created": True,
        "proposal_id": proposal.proposal_id,
        "summary": proposal.summary,
        "action_type": "complete_task",
        "provider": provider,
        "risk_level": proposal.risk_level,
    }


def handle_propose_grocery_items(tool_input: dict, ctx: ToolContext) -> dict:
    """Propose adding items to a grocery/shopping list."""
    # Validate required fields
    if "list_name" not in tool_input or tool_input["list_name"] is None:
        raise ToolInputError("propose_grocery_items", "list_name", "list_name is required")
    if "items" not in tool_input or tool_input["items"] is None:
        raise ToolInputError("propose_grocery_items", "items", "items is required")

    provider = tool_input.get("provider") or _preferred_task_provider(ctx)

    payload: dict[str, Any] = {
        "list_name": tool_input["list_name"],
        "items": tool_input["items"],
    }

    items = tool_input["items"]
    summary = f"Add {len(items)} item(s) to the '{tool_input['list_name']}' list in {provider}."

    proposal = build_action_proposal(
        provider=provider,
        action_type="upsert_grocery_items",
        resource_type="task_list",
        payload=payload,
        summary=summary,
        ttl_minutes=ctx.config.proposal_ttl_minutes,
    )
    ctx.proposals_accumulator.append(proposal)

    return {
        "proposal_created": True,
        "proposal_id": proposal.proposal_id,
        "summary": proposal.summary,
        "action_type": "upsert_grocery_items",
        "provider": provider,
        "risk_level": proposal.risk_level,
        "item_count": len(items),
    }


# ---------------------------------------------------------------------------
# Provider preference helpers
# ---------------------------------------------------------------------------


def _preferred_task_provider(ctx: ToolContext) -> str:
    """Return the preferred task provider from the registry."""
    try:
        providers = list(ctx.registry.providers())
        for p in providers:
            if p in {"google_tasks", "microsoft_todo"}:
                return p
    except Exception:
        pass
    return "google_tasks"


def _preferred_calendar_provider(ctx: ToolContext) -> str:
    """Return the preferred calendar provider from the registry."""
    try:
        providers = list(ctx.registry.providers())
        for p in providers:
            if p in {"google_calendar", "microsoft_calendar"}:
                return p
    except Exception:
        pass
    return "google_calendar"


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_HANDLERS = {
    "get_calendar_events": handle_get_calendar_events,
    "get_task_lists": handle_get_task_lists,
    "get_tasks": handle_get_tasks,
    "get_meeting_documents": handle_get_meeting_documents,
    "get_grocery_lists": handle_get_grocery_lists,
    "propose_calendar_event": handle_propose_calendar_event,
    "propose_task_update": handle_propose_task_update,
    "propose_task_complete": handle_propose_task_complete,
    "propose_grocery_items": handle_propose_grocery_items,
}


def dispatch(tool_name: str, tool_input: dict, ctx: ToolContext) -> dict:
    """Route a tool call to the appropriate handler.

    Raises KeyError for unknown tool names.
    """
    handler = _HANDLERS[tool_name]  # raises KeyError for unknown tools
    return handler(tool_input, ctx)
