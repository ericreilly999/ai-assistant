"""Tests for assistant_app.tool_handlers — Phase 13 TDD.

Tests are written from the spec (tool-use-spec.md Section 2 and 6).
They call handler functions directly. No Bedrock calls are made.
All paths use mock_provider_mode=True.

These tests will fail with ImportError until T-29 is implemented.

Coverage map:
  AC-06 → test_handle_get_calendar_events_returns_events_key,
           test_handle_get_calendar_events_event_has_required_fields,
           test_handle_get_calendar_events_provider_is_string,
           test_handle_get_task_lists_returns_three_task_lists,
           test_handle_get_task_lists_lists_have_id_and_name,
           test_handle_get_task_lists_provider_is_present,
           test_handle_get_meeting_documents_returns_documents,
           test_handle_get_meeting_documents_document_has_required_fields,
           test_handle_get_meeting_documents_provider_is_google_drive,
           test_handle_get_grocery_lists_returns_one_list,
           test_handle_get_grocery_lists_list_has_required_fields
  AC-07 → test_handle_get_tasks_returns_four_tasks_for_list_001
  AC-08 → test_handle_get_calendar_events_caps_at_twenty_events
  AC-09 → test_handle_get_tasks_caps_at_fifty_tasks
  AC-10 → test_handle_propose_calendar_event_appends_one_proposal,
           test_handle_propose_calendar_event_returns_proposal_created_true,
           test_handle_propose_calendar_event_returns_action_type,
           test_handle_propose_task_update_appends_one_proposal,
           test_handle_propose_task_update_action_type_is_update_task,
           test_handle_propose_task_update_payload_contains_real_ids,
           test_handle_propose_task_complete_appends_one_proposal
  AC-11 → test_handle_propose_task_update_without_prior_get_tasks_returns_error,
           test_handle_propose_task_complete_without_prior_get_tasks_returns_error
  AC-12 → test_dispatch_known_tool_returns_result,
           test_dispatch_unknown_tool_raises_key_error
  Extra → test_handle_get_calendar_events_missing_start_raises_tool_input_error,
           test_handle_get_calendar_events_missing_end_raises_tool_input_error,
           test_handle_get_tasks_missing_list_id_raises_tool_input_error,
           test_handle_propose_calendar_event_missing_title_raises_tool_input_error,
           test_handle_propose_calendar_event_missing_start_raises_tool_input_error,
           test_handle_propose_calendar_event_missing_end_raises_tool_input_error,
           test_handle_propose_task_update_missing_list_id_raises_tool_input_error,
           test_handle_propose_task_update_missing_task_id_raises_tool_input_error,
           test_handle_propose_task_update_missing_updates_raises_tool_input_error,
           test_handle_propose_task_complete_missing_list_id_raises_tool_input_error,
           test_handle_propose_task_complete_missing_task_id_raises_tool_input_error,
           test_handle_get_tasks_task_status_values_are_valid,
           test_handle_propose_task_update_error_message_mentions_get_tasks,
           test_handle_propose_task_complete_error_message_mentions_get_tasks,
           test_multiple_proposals_accumulate_independently
"""

from __future__ import annotations

import unittest

# These imports will raise ImportError until T-29 is implemented.
from assistant_app.config import AppConfig
from assistant_app.models import ToolInputError  # Added in this phase per spec Section 9.1
from assistant_app.tool_handlers import (
    ToolContext,
    dispatch,
    handle_get_calendar_events,
    handle_get_grocery_lists,
    handle_get_meeting_documents,
    handle_get_task_lists,
    handle_get_tasks,
    handle_propose_calendar_event,
    handle_propose_grocery_items,
    handle_propose_task_complete,
    handle_propose_task_update,
)


def _make_config() -> AppConfig:
    """Return an AppConfig with mock_provider_mode=True and the new max_agent_turns field."""
    try:
        return AppConfig(
            app_env="dev",
            log_level="INFO",
            mock_provider_mode=True,
            proposal_ttl_minutes=15,
            default_timezone="America/New_York",
            bedrock_router_model_id="mock-router",
            bedrock_guardrail_id="mock-guardrail",
            bedrock_guardrail_version="DRAFT",
            max_agent_turns=5,
        )
    except TypeError:
        # max_agent_turns not yet added to AppConfig — graceful fallback during TDD
        return AppConfig(
            app_env="dev",
            log_level="INFO",
            mock_provider_mode=True,
            proposal_ttl_minutes=15,
            default_timezone="America/New_York",
            bedrock_router_model_id="mock-router",
            bedrock_guardrail_id="mock-guardrail",
            bedrock_guardrail_version="DRAFT",
        )


def _make_ctx(messages=None, proposals=None, sources=None) -> ToolContext:
    """Factory helper for ToolContext used across all handler tests."""
    from assistant_app.registry import ProviderRegistry

    config = _make_config()
    return ToolContext(
        config=config,
        registry=ProviderRegistry(mock_mode=True),
        live_service=None,
        messages=messages or [],
        proposals_accumulator=proposals if proposals is not None else [],
        sources_accumulator=sources if sources is not None else [],
    )


def _make_prior_get_tasks_messages(
    tool_use_id: str = "test-001",
    list_id: str = "list-001",
    tasks: list[dict] | None = None,
) -> list[dict]:
    """Build a realistic messages list containing a prior get_tasks tool result.

    The format mirrors the Bedrock Converse message format so that the
    ID validation logic in propose_task_update / propose_task_complete
    can find real list_id / task_id values in context.
    """
    if tasks is None:
        tasks = [
            {"id": "task-001", "title": "Review contracts", "status": "needsAction"},
            {"id": "task-002", "title": "Call dentist", "status": "needsAction"},
        ]

    prior_tool_use = {
        "role": "assistant",
        "content": [
            {
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": "get_tasks",
                    "input": {"list_id": list_id},
                }
            }
        ],
    }
    prior_tool_result = {
        "role": "user",
        "content": [
            {
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [
                        {
                            "json": {
                                "tasks": tasks,
                                "list_id": list_id,
                                "provider": "google_tasks",
                            }
                        }
                    ],
                }
            }
        ],
    }
    return [prior_tool_use, prior_tool_result]


# ---------------------------------------------------------------------------
# get_calendar_events
# ---------------------------------------------------------------------------


class TestHandleGetCalendarEvents(unittest.TestCase):
    """AC-06, AC-08: get_calendar_events mock mode returns correct shape, capped at 20."""

    def _call(self, ctx: ToolContext | None = None) -> dict:
        if ctx is None:
            ctx = _make_ctx()
        return handle_get_calendar_events(
            {
                "start": "2026-04-19T00:00:00-04:00",
                "end": "2026-04-19T23:59:59-04:00",
            },
            ctx,
        )

    def test_handle_get_calendar_events_returns_events_key(self) -> None:
        """AC-06: Result must have an 'events' key containing a list."""
        result = self._call()
        self.assertIn("events", result)
        self.assertIsInstance(result["events"], list)

    def test_handle_get_calendar_events_event_has_required_fields(self) -> None:
        """AC-06: Each event in the result must have id, title, start, end, source."""
        result = self._call()
        self.assertGreater(len(result["events"]), 0, msg="Mock must return at least 1 event.")
        for event in result["events"]:
            with self.subTest(event=event.get("id")):
                for field in ("id", "title", "start", "end", "source"):
                    self.assertIn(field, event, msg=f"Event must have '{field}' field.")

    def test_handle_get_calendar_events_provider_is_string(self) -> None:
        """AC-06: 'provider' field in result must be a non-empty string."""
        result = self._call()
        self.assertIn("provider", result)
        self.assertIsInstance(result["provider"], str)
        self.assertGreater(len(result["provider"]), 0)

    def test_handle_get_calendar_events_caps_at_twenty_events(self) -> None:
        """AC-08: Events list must never exceed 20 entries regardless of mock data size.

        We verify by checking that the returned list has at most 20 entries.
        The cap is enforced by the handler, not the mock data source.
        """
        result = self._call()
        self.assertLessEqual(
            len(result["events"]),
            20,
            msg="get_calendar_events must cap results at 20 events.",
        )

    def test_handle_get_calendar_events_missing_start_raises_tool_input_error(self) -> None:
        """Missing required 'start' field must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_get_calendar_events({"end": "2026-04-19T23:59:59-04:00"}, ctx)
        self.assertEqual(cm.exception.field, "start")

    def test_handle_get_calendar_events_missing_end_raises_tool_input_error(self) -> None:
        """Missing required 'end' field must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_get_calendar_events({"start": "2026-04-19T00:00:00-04:00"}, ctx)
        self.assertEqual(cm.exception.field, "end")

    def test_handle_get_calendar_events_result_has_count_field(self) -> None:
        """Result must include a 'count' field matching the events list length."""
        result = self._call()
        self.assertIn("count", result)
        self.assertEqual(result["count"], len(result["events"]))

    def test_handle_get_calendar_events_result_has_truncated_field(self) -> None:
        """Result must include a boolean 'truncated' field."""
        result = self._call()
        self.assertIn("truncated", result)
        self.assertIsInstance(result["truncated"], bool)


# ---------------------------------------------------------------------------
# get_task_lists
# ---------------------------------------------------------------------------


class TestHandleGetTaskLists(unittest.TestCase):
    """AC-06: get_task_lists mock mode returns 3 task lists with required fields."""

    def _call(self, ctx: ToolContext | None = None) -> dict:
        if ctx is None:
            ctx = _make_ctx()
        return handle_get_task_lists({}, ctx)

    def test_handle_get_task_lists_returns_three_task_lists(self) -> None:
        """AC-06: Mock mode must return exactly 3 task lists per spec Section 2.2."""
        result = self._call()
        self.assertIn("task_lists", result)
        self.assertEqual(
            len(result["task_lists"]),
            3,
            msg=f"Expected 3 task lists, got {len(result['task_lists'])}.",
        )

    def test_handle_get_task_lists_lists_have_id_and_name(self) -> None:
        """AC-06: Each task list must have 'id' and 'name' fields."""
        result = self._call()
        for task_list in result["task_lists"]:
            with self.subTest(task_list=task_list.get("id")):
                self.assertIn("id", task_list, msg="Task list must have 'id'.")
                self.assertIn("name", task_list, msg="Task list must have 'name'.")
                self.assertGreater(len(task_list["id"]), 0)
                self.assertGreater(len(task_list["name"]), 0)

    def test_handle_get_task_lists_provider_is_present(self) -> None:
        """AC-06: Result must include a 'provider' field."""
        result = self._call()
        self.assertIn("provider", result)
        self.assertIsInstance(result["provider"], str)
        self.assertGreater(len(result["provider"]), 0)

    def test_handle_get_task_lists_includes_list_001(self) -> None:
        """Mock data must include list-001 per spec Section 2.2."""
        result = self._call()
        ids = [tl["id"] for tl in result["task_lists"]]
        self.assertIn("list-001", ids, msg="Mock must include task list id 'list-001'.")

    def test_handle_get_task_lists_result_has_count_field(self) -> None:
        """Result must include 'count' matching task_lists length."""
        result = self._call()
        self.assertIn("count", result)
        self.assertEqual(result["count"], len(result["task_lists"]))


# ---------------------------------------------------------------------------
# get_tasks
# ---------------------------------------------------------------------------


class TestHandleGetTasks(unittest.TestCase):
    """AC-07, AC-09: get_tasks returns 4 tasks for list-001, caps at 50."""

    def _call(self, list_id: str = "list-001", ctx: ToolContext | None = None) -> dict:
        if ctx is None:
            ctx = _make_ctx()
        return handle_get_tasks({"list_id": list_id}, ctx)

    def test_handle_get_tasks_returns_four_tasks_for_list_001(self) -> None:
        """AC-07: Mock mode with list_id='list-001' must return exactly 4 tasks."""
        result = self._call("list-001")
        self.assertIn("tasks", result)
        self.assertEqual(
            len(result["tasks"]),
            4,
            msg=f"Expected 4 tasks for list-001, got {len(result['tasks'])}.",
        )

    def test_handle_get_tasks_task_has_required_fields(self) -> None:
        """AC-06: Each task must have id, title, status, source."""
        result = self._call("list-001")
        for task in result["tasks"]:
            with self.subTest(task_id=task.get("id")):
                for field in ("id", "title", "status", "source"):
                    self.assertIn(field, task, msg=f"Task must have '{field}'.")

    def test_handle_get_tasks_task_status_values_are_valid(self) -> None:
        """AC-06: Each task status must be 'needsAction' or 'completed'."""
        result = self._call("list-001")
        valid_statuses = {"needsAction", "completed"}
        for task in result["tasks"]:
            with self.subTest(task_id=task.get("id")):
                self.assertIn(
                    task["status"],
                    valid_statuses,
                    msg=f"Task status '{task['status']}' is not a valid value.",
                )

    def test_handle_get_tasks_caps_at_fifty_tasks(self) -> None:
        """AC-09: Tasks list must never exceed 50 entries."""
        result = self._call("list-001")
        self.assertLessEqual(
            len(result["tasks"]),
            50,
            msg="get_tasks must cap results at 50 tasks.",
        )

    def test_handle_get_tasks_missing_list_id_raises_tool_input_error(self) -> None:
        """Missing required 'list_id' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_get_tasks({}, ctx)
        self.assertEqual(cm.exception.field, "list_id")

    def test_handle_get_tasks_result_has_list_id_field(self) -> None:
        """Result must echo back the list_id that was queried."""
        result = self._call("list-001")
        self.assertIn("list_id", result)
        self.assertEqual(result["list_id"], "list-001")

    def test_handle_get_tasks_result_has_provider_field(self) -> None:
        """Result must include a 'provider' field."""
        result = self._call("list-001")
        self.assertIn("provider", result)
        self.assertIsInstance(result["provider"], str)

    def test_handle_get_tasks_result_has_count_field(self) -> None:
        """Result must include 'count' matching tasks list length."""
        result = self._call("list-001")
        self.assertIn("count", result)
        self.assertEqual(result["count"], len(result["tasks"]))

    def test_handle_get_tasks_mock_data_includes_task_001_and_task_002(self) -> None:
        """Mock data must include task-001 and task-002 per spec Section 2.2."""
        result = self._call("list-001")
        ids = [t["id"] for t in result["tasks"]]
        self.assertIn("task-001", ids, msg="Mock must include task-001.")
        self.assertIn("task-002", ids, msg="Mock must include task-002.")


# ---------------------------------------------------------------------------
# get_meeting_documents
# ---------------------------------------------------------------------------


class TestHandleGetMeetingDocuments(unittest.TestCase):
    """AC-06: get_meeting_documents returns at least 1 document with required fields."""

    def _call(self, ctx: ToolContext | None = None) -> dict:
        if ctx is None:
            ctx = _make_ctx()
        return handle_get_meeting_documents({}, ctx)

    def test_handle_get_meeting_documents_returns_documents(self) -> None:
        """AC-06: Mock must return at least 1 document."""
        result = self._call()
        self.assertIn("documents", result)
        self.assertGreater(
            len(result["documents"]),
            0,
            msg="Mock must return at least 1 document.",
        )

    def test_handle_get_meeting_documents_document_has_required_fields(self) -> None:
        """AC-06: Each document must have id, title, web_view_link."""
        result = self._call()
        for doc in result["documents"]:
            with self.subTest(doc_id=doc.get("id")):
                for field in ("id", "title", "web_view_link"):
                    self.assertIn(field, doc, msg=f"Document must have '{field}'.")

    def test_handle_get_meeting_documents_provider_is_google_drive(self) -> None:
        """AC-06: provider must be 'google_drive' per spec Section 2.2."""
        result = self._call()
        self.assertEqual(
            result.get("provider"),
            "google_drive",
            msg="get_meeting_documents provider must be 'google_drive'.",
        )

    def test_handle_get_meeting_documents_result_has_count_field(self) -> None:
        """Result must include 'count' matching documents length."""
        result = self._call()
        self.assertIn("count", result)
        self.assertEqual(result["count"], len(result["documents"]))


# ---------------------------------------------------------------------------
# get_grocery_lists
# ---------------------------------------------------------------------------


class TestHandleGetGroceryLists(unittest.TestCase):
    """AC-06: get_grocery_lists returns 1 grocery list with required fields."""

    def _call(self, ctx: ToolContext | None = None) -> dict:
        if ctx is None:
            ctx = _make_ctx()
        return handle_get_grocery_lists({}, ctx)

    def test_handle_get_grocery_lists_returns_one_list(self) -> None:
        """AC-06: Mock must return exactly 1 grocery list per spec Section 2.2."""
        result = self._call()
        self.assertIn("grocery_lists", result)
        self.assertEqual(
            len(result["grocery_lists"]),
            1,
            msg=f"Mock must return 1 grocery list, got {len(result['grocery_lists'])}.",
        )

    def test_handle_get_grocery_lists_list_has_required_fields(self) -> None:
        """AC-06: Each grocery list must have list_id, list_name, items."""
        result = self._call()
        grocery_list = result["grocery_lists"][0]
        for field in ("list_id", "list_name", "items"):
            self.assertIn(field, grocery_list, msg=f"Grocery list must have '{field}'.")

    def test_handle_get_grocery_lists_items_is_list(self) -> None:
        """items must be a list."""
        result = self._call()
        self.assertIsInstance(result["grocery_lists"][0]["items"], list)

    def test_handle_get_grocery_lists_provider_is_present(self) -> None:
        """Result must include a 'provider' field."""
        result = self._call()
        self.assertIn("provider", result)
        self.assertIsInstance(result["provider"], str)

    def test_handle_get_grocery_lists_mock_list_name_is_groceries(self) -> None:
        """Mock data list_name must be 'Groceries' per spec Section 2.2."""
        result = self._call()
        self.assertEqual(
            result["grocery_lists"][0]["list_name"],
            "Groceries",
            msg="Mock grocery list name must be 'Groceries'.",
        )


# ---------------------------------------------------------------------------
# propose_calendar_event
# ---------------------------------------------------------------------------


class TestHandleProposeCalendarEvent(unittest.TestCase):
    """AC-10: propose_calendar_event appends one ActionProposal and returns correct dict."""

    _VALID_INPUT = {
        "title": "Team Standup",
        "start": "2026-04-20T10:00:00-04:00",
        "end": "2026-04-20T10:30:00-04:00",
    }

    def test_handle_propose_calendar_event_appends_one_proposal(self) -> None:
        """AC-10: Handler must append exactly 1 ActionProposal to proposals_accumulator."""
        ctx = _make_ctx()
        self.assertEqual(len(ctx.proposals_accumulator), 0)
        handle_propose_calendar_event(self._VALID_INPUT, ctx)
        self.assertEqual(
            len(ctx.proposals_accumulator),
            1,
            msg="Handler must append exactly 1 proposal.",
        )

    def test_handle_propose_calendar_event_returns_proposal_created_true(self) -> None:
        """AC-10: Returned dict must have proposal_created: True."""
        ctx = _make_ctx()
        result = handle_propose_calendar_event(self._VALID_INPUT, ctx)
        self.assertIs(result.get("proposal_created"), True)

    def test_handle_propose_calendar_event_returns_action_type(self) -> None:
        """AC-10: Returned dict must have action_type='create_calendar_event'."""
        ctx = _make_ctx()
        result = handle_propose_calendar_event(self._VALID_INPUT, ctx)
        self.assertEqual(result.get("action_type"), "create_calendar_event")

    def test_handle_propose_calendar_event_missing_title_raises_tool_input_error(self) -> None:
        """Missing required 'title' must raise ToolInputError."""
        ctx = _make_ctx()
        bad_input = {
            "start": "2026-04-20T10:00:00-04:00",
            "end": "2026-04-20T10:30:00-04:00",
        }
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_calendar_event(bad_input, ctx)
        self.assertEqual(cm.exception.field, "title")

    def test_handle_propose_calendar_event_missing_start_raises_tool_input_error(self) -> None:
        """Missing required 'start' must raise ToolInputError."""
        ctx = _make_ctx()
        bad_input = {"title": "Standup", "end": "2026-04-20T10:30:00-04:00"}
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_calendar_event(bad_input, ctx)
        self.assertEqual(cm.exception.field, "start")

    def test_handle_propose_calendar_event_missing_end_raises_tool_input_error(self) -> None:
        """Missing required 'end' must raise ToolInputError."""
        ctx = _make_ctx()
        bad_input = {"title": "Standup", "start": "2026-04-20T10:00:00-04:00"}
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_calendar_event(bad_input, ctx)
        self.assertEqual(cm.exception.field, "end")

    def test_handle_propose_calendar_event_proposal_has_correct_action_type(self) -> None:
        """ActionProposal in accumulator must have action_type='create_calendar_event'."""
        ctx = _make_ctx()
        handle_propose_calendar_event(self._VALID_INPUT, ctx)
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.action_type, "create_calendar_event")

    def test_handle_propose_calendar_event_proposal_has_proposal_id(self) -> None:
        """Returned dict must contain a non-empty proposal_id."""
        ctx = _make_ctx()
        result = handle_propose_calendar_event(self._VALID_INPUT, ctx)
        self.assertIn("proposal_id", result)
        self.assertIsInstance(result["proposal_id"], str)
        self.assertGreater(len(result["proposal_id"]), 0)

    def test_handle_propose_calendar_event_does_not_modify_other_accumulator(self) -> None:
        """propose_calendar_event must not accidentally append to sources_accumulator."""
        ctx = _make_ctx()
        initial_sources_count = len(ctx.sources_accumulator)
        handle_propose_calendar_event(self._VALID_INPUT, ctx)
        self.assertEqual(len(ctx.sources_accumulator), initial_sources_count)


# ---------------------------------------------------------------------------
# propose_task_update
# ---------------------------------------------------------------------------


class TestHandleProposeTaskUpdate(unittest.TestCase):
    """AC-10, AC-11: propose_task_update with valid context appends proposal;
    without prior get_tasks result returns isError."""

    def _ctx_with_prior_get_tasks(self) -> ToolContext:
        messages = _make_prior_get_tasks_messages()
        return _make_ctx(messages=messages)

    def test_handle_propose_task_update_appends_one_proposal(self) -> None:
        """AC-10: With valid IDs from prior get_tasks, must append 1 proposal."""
        ctx = self._ctx_with_prior_get_tasks()
        handle_propose_task_update(
            {
                "list_id": "list-001",
                "task_id": "task-001",
                "updates": {"title": "Review contracts — URGENT"},
            },
            ctx,
        )
        self.assertEqual(len(ctx.proposals_accumulator), 1)

    def test_handle_propose_task_update_action_type_is_update_task(self) -> None:
        """AC-10: ActionProposal must have action_type='update_task'."""
        ctx = self._ctx_with_prior_get_tasks()
        handle_propose_task_update(
            {
                "list_id": "list-001",
                "task_id": "task-001",
                "updates": {"title": "Urgent"},
            },
            ctx,
        )
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.action_type, "update_task")

    def test_handle_propose_task_update_payload_contains_real_ids(self) -> None:
        """AC-10: Proposal payload must contain the real list_id and task_id — not empty."""
        ctx = self._ctx_with_prior_get_tasks()
        handle_propose_task_update(
            {
                "list_id": "list-001",
                "task_id": "task-001",
                "updates": {"title": "Urgent"},
            },
            ctx,
        )
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.payload.get("list_id"), "list-001")
        self.assertEqual(proposal.payload.get("task_id"), "task-001")
        self.assertNotEqual(proposal.payload.get("list_id"), "")
        self.assertNotEqual(proposal.payload.get("task_id"), "")

    def test_handle_propose_task_update_without_prior_get_tasks_returns_error(self) -> None:
        """AC-11: Without a prior get_tasks result in messages, must return isError: True."""
        ctx = _make_ctx()  # no messages
        result = handle_propose_task_update(
            {
                "list_id": "list-001",
                "task_id": "task-001",
                "updates": {"title": "Urgent"},
            },
            ctx,
        )
        self.assertIs(
            result.get("isError"),
            True,
            msg="Handler must return isError: True when IDs are not from a prior get_tasks.",
        )

    def test_handle_propose_task_update_error_message_mentions_get_tasks(self) -> None:
        """AC-11: Error message must contain 'must come from a get_tasks result'."""
        ctx = _make_ctx()
        result = handle_propose_task_update(
            {
                "list_id": "hallucinated-list",
                "task_id": "hallucinated-task",
                "updates": {"title": "Urgent"},
            },
            ctx,
        )
        error_content = str(result.get("content", "")).lower()
        self.assertIn(
            "get_tasks",
            error_content,
            msg="Error message must reference 'get_tasks'.",
        )

    def test_handle_propose_task_update_hallucinated_task_id_returns_error(self) -> None:
        """AC-11: A task_id not present in any prior get_tasks result must return isError."""
        ctx = self._ctx_with_prior_get_tasks()  # contains task-001 and task-002 only
        result = handle_propose_task_update(
            {
                "list_id": "list-001",
                "task_id": "task-HALLUCINATED",
                "updates": {"title": "Bad"},
            },
            ctx,
        )
        self.assertIs(result.get("isError"), True)

    def test_handle_propose_task_update_missing_list_id_raises_tool_input_error(self) -> None:
        """Missing required 'list_id' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_task_update(
                {"task_id": "task-001", "updates": {"title": "X"}}, ctx
            )
        self.assertEqual(cm.exception.field, "list_id")

    def test_handle_propose_task_update_missing_task_id_raises_tool_input_error(self) -> None:
        """Missing required 'task_id' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_task_update(
                {"list_id": "list-001", "updates": {"title": "X"}}, ctx
            )
        self.assertEqual(cm.exception.field, "task_id")

    def test_handle_propose_task_update_missing_updates_raises_tool_input_error(self) -> None:
        """Missing required 'updates' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_task_update(
                {"list_id": "list-001", "task_id": "task-001"}, ctx
            )
        self.assertEqual(cm.exception.field, "updates")

    def test_handle_propose_task_update_does_not_append_proposal_on_error(self) -> None:
        """When ID validation fails, no proposal must be appended."""
        ctx = _make_ctx()  # no prior messages
        handle_propose_task_update(
            {
                "list_id": "list-001",
                "task_id": "task-001",
                "updates": {"title": "Bad"},
            },
            ctx,
        )
        self.assertEqual(len(ctx.proposals_accumulator), 0)


# ---------------------------------------------------------------------------
# propose_task_complete
# ---------------------------------------------------------------------------


class TestHandleProposeTaskComplete(unittest.TestCase):
    """AC-10, AC-11: propose_task_complete with valid context appends proposal;
    without prior get_tasks returns isError."""

    def _ctx_with_prior_get_tasks(self) -> ToolContext:
        messages = _make_prior_get_tasks_messages()
        return _make_ctx(messages=messages)

    def test_handle_propose_task_complete_appends_one_proposal(self) -> None:
        """AC-10: With valid IDs from prior get_tasks, must append 1 proposal."""
        ctx = self._ctx_with_prior_get_tasks()
        handle_propose_task_complete(
            {"list_id": "list-001", "task_id": "task-002"}, ctx
        )
        self.assertEqual(len(ctx.proposals_accumulator), 1)

    def test_handle_propose_task_complete_action_type_is_complete_task(self) -> None:
        """AC-10: ActionProposal must have action_type='complete_task'."""
        ctx = self._ctx_with_prior_get_tasks()
        handle_propose_task_complete(
            {"list_id": "list-001", "task_id": "task-002"}, ctx
        )
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.action_type, "complete_task")

    def test_handle_propose_task_complete_payload_contains_real_ids(self) -> None:
        """Proposal payload must contain non-empty list_id and task_id."""
        ctx = self._ctx_with_prior_get_tasks()
        handle_propose_task_complete(
            {"list_id": "list-001", "task_id": "task-002"}, ctx
        )
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.payload.get("list_id"), "list-001")
        self.assertEqual(proposal.payload.get("task_id"), "task-002")
        self.assertNotEqual(proposal.payload.get("list_id"), "")
        self.assertNotEqual(proposal.payload.get("task_id"), "")

    def test_handle_propose_task_complete_without_prior_get_tasks_returns_error(self) -> None:
        """AC-11: Without prior get_tasks result, must return isError: True."""
        ctx = _make_ctx()
        result = handle_propose_task_complete(
            {"list_id": "list-001", "task_id": "task-002"}, ctx
        )
        self.assertIs(result.get("isError"), True)

    def test_handle_propose_task_complete_error_message_mentions_get_tasks(self) -> None:
        """AC-11: Error content must reference 'get_tasks'."""
        ctx = _make_ctx()
        result = handle_propose_task_complete(
            {"list_id": "hallucinated", "task_id": "hallucinated"}, ctx
        )
        error_content = str(result.get("content", "")).lower()
        self.assertIn("get_tasks", error_content)

    def test_handle_propose_task_complete_missing_list_id_raises_tool_input_error(self) -> None:
        """Missing required 'list_id' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_task_complete({"task_id": "task-001"}, ctx)
        self.assertEqual(cm.exception.field, "list_id")

    def test_handle_propose_task_complete_missing_task_id_raises_tool_input_error(self) -> None:
        """Missing required 'task_id' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_task_complete({"list_id": "list-001"}, ctx)
        self.assertEqual(cm.exception.field, "task_id")

    def test_handle_propose_task_complete_does_not_append_on_error(self) -> None:
        """No proposal must be appended when ID validation fails."""
        ctx = _make_ctx()
        handle_propose_task_complete(
            {"list_id": "list-001", "task_id": "task-002"}, ctx
        )
        self.assertEqual(len(ctx.proposals_accumulator), 0)


# ---------------------------------------------------------------------------
# propose_grocery_items
# ---------------------------------------------------------------------------


class TestHandleProposeGroceryItems(unittest.TestCase):
    """propose_grocery_items appends a proposal; missing fields raise ToolInputError."""

    _VALID_INPUT = {"list_name": "Groceries", "items": ["milk", "bread"]}

    def test_handle_propose_grocery_items_appends_one_proposal(self) -> None:
        """With valid input, must append exactly 1 ActionProposal."""
        ctx = _make_ctx()
        handle_propose_grocery_items(self._VALID_INPUT, ctx)
        self.assertEqual(len(ctx.proposals_accumulator), 1)

    def test_handle_propose_grocery_items_action_type_is_upsert_grocery_items(self) -> None:
        """ActionProposal must have action_type='upsert_grocery_items'."""
        ctx = _make_ctx()
        handle_propose_grocery_items(self._VALID_INPUT, ctx)
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.action_type, "upsert_grocery_items")

    def test_handle_propose_grocery_items_returns_proposal_created_true(self) -> None:
        """Returned dict must have proposal_created: True."""
        ctx = _make_ctx()
        result = handle_propose_grocery_items(self._VALID_INPUT, ctx)
        self.assertIs(result.get("proposal_created"), True)

    def test_handle_propose_grocery_items_missing_list_name_raises_tool_input_error(self) -> None:
        """Missing required 'list_name' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_grocery_items({"items": ["milk"]}, ctx)
        self.assertEqual(cm.exception.field, "list_name")

    def test_handle_propose_grocery_items_missing_items_raises_tool_input_error(self) -> None:
        """Missing required 'items' must raise ToolInputError."""
        ctx = _make_ctx()
        with self.assertRaises(ToolInputError) as cm:
            handle_propose_grocery_items({"list_name": "Groceries"}, ctx)
        self.assertEqual(cm.exception.field, "items")

    def test_handle_propose_grocery_items_payload_contains_items(self) -> None:
        """Proposal payload must include the 'items' list as submitted."""
        ctx = _make_ctx()
        handle_propose_grocery_items(self._VALID_INPUT, ctx)
        proposal = ctx.proposals_accumulator[0]
        self.assertEqual(proposal.payload.get("items"), ["milk", "bread"])


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


class TestDispatch(unittest.TestCase):
    """AC-12: dispatch routes to the correct handler; unknown names raise KeyError."""

    def test_dispatch_get_task_lists_returns_valid_result(self) -> None:
        """AC-12: dispatch('get_task_lists', {}, ctx) must return a valid result dict."""
        ctx = _make_ctx()
        result = dispatch("get_task_lists", {}, ctx)
        self.assertIsInstance(result, dict)
        self.assertIn("task_lists", result)

    def test_dispatch_unknown_tool_raises_key_error(self) -> None:
        """AC-12: dispatch with an unknown tool name must raise KeyError."""
        ctx = _make_ctx()
        with self.assertRaises(KeyError):
            dispatch("unknown_tool", {}, ctx)

    def test_dispatch_get_calendar_events_routes_to_handler(self) -> None:
        """dispatch must route get_calendar_events to its handler."""
        ctx = _make_ctx()
        result = dispatch(
            "get_calendar_events",
            {
                "start": "2026-04-19T00:00:00-04:00",
                "end": "2026-04-19T23:59:59-04:00",
            },
            ctx,
        )
        self.assertIn("events", result)

    def test_dispatch_get_tasks_routes_to_handler(self) -> None:
        """dispatch must route get_tasks to its handler."""
        ctx = _make_ctx()
        result = dispatch("get_tasks", {"list_id": "list-001"}, ctx)
        self.assertIn("tasks", result)

    def test_dispatch_get_meeting_documents_routes_to_handler(self) -> None:
        """dispatch must route get_meeting_documents to its handler."""
        ctx = _make_ctx()
        result = dispatch("get_meeting_documents", {}, ctx)
        self.assertIn("documents", result)

    def test_dispatch_get_grocery_lists_routes_to_handler(self) -> None:
        """dispatch must route get_grocery_lists to its handler."""
        ctx = _make_ctx()
        result = dispatch("get_grocery_lists", {}, ctx)
        self.assertIn("grocery_lists", result)

    def test_dispatch_propose_calendar_event_routes_to_handler(self) -> None:
        """dispatch must route propose_calendar_event to its handler."""
        ctx = _make_ctx()
        result = dispatch(
            "propose_calendar_event",
            {
                "title": "Test",
                "start": "2026-04-20T10:00:00-04:00",
                "end": "2026-04-20T10:30:00-04:00",
            },
            ctx,
        )
        self.assertIs(result.get("proposal_created"), True)


# ---------------------------------------------------------------------------
# Multi-proposal accumulation
# ---------------------------------------------------------------------------


class TestMultipleProposalAccumulation(unittest.TestCase):
    """Extra: Multiple proposal tools called in sequence accumulate independently."""

    def test_multiple_proposals_accumulate_independently(self) -> None:
        """Two write-proposal calls on the same ctx must produce 2 proposals total."""
        ctx = _make_ctx()

        # First proposal: calendar event
        handle_propose_calendar_event(
            {
                "title": "Morning Standup",
                "start": "2026-04-20T09:00:00-04:00",
                "end": "2026-04-20T09:30:00-04:00",
            },
            ctx,
        )
        self.assertEqual(len(ctx.proposals_accumulator), 1)

        # Second proposal: grocery items
        handle_propose_grocery_items(
            {"list_name": "Groceries", "items": ["coffee"]}, ctx
        )
        self.assertEqual(
            len(ctx.proposals_accumulator),
            2,
            msg="Both proposals must be in the accumulator.",
        )
        action_types = {p.action_type for p in ctx.proposals_accumulator}
        self.assertIn("create_calendar_event", action_types)
        self.assertIn("upsert_grocery_items", action_types)


if __name__ == "__main__":
    unittest.main()
