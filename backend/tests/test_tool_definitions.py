"""Tests for assistant_app.tool_definitions — Phase 13 TDD.

These tests are written from the spec (tool-use-spec.md) before the implementation
exists. Every test will fail with ImportError until T-28 is implemented.

Coverage map:
  AC-01 → test_tool_definitions_has_exactly_nine_entries
  AC-02 → test_each_tool_has_required_bedrock_fields,
           test_each_tool_name_is_non_empty,
           test_each_tool_description_is_non_empty,
           test_each_tool_input_schema_is_non_empty
  AC-03 → test_count_tool_definition_tokens_within_budget
  AC-04 → test_build_tool_config_google_calendar_includes_calendar_tools,
           test_build_tool_config_google_calendar_excludes_task_tools,
           test_build_tool_config_google_calendar_excludes_grocery_tools
  AC-05 → test_agent_system_prompt_is_non_empty,
           test_agent_system_prompt_contains_data_before_writes
  Extra → test_build_tool_config_empty_list_returns_all_tools,
           test_build_tool_config_none_returns_all_tools,
           test_each_tool_input_schema_is_valid_json_schema,
           test_write_proposal_tools_have_required_id_fields,
           test_full_tool_config_includes_read_tools,
           test_tool_names_are_unique,
           test_build_tool_config_google_tasks_includes_task_tools,
           test_build_tool_config_google_tasks_excludes_calendar_tools,
           test_get_meeting_documents_in_google_drive_config,
           test_get_grocery_lists_in_google_tasks_config,
           test_propose_calendar_event_in_google_calendar_config,
           test_propose_grocery_items_in_google_tasks_config
"""

from __future__ import annotations

import unittest

# This import will raise ImportError until T-28 is implemented.
# That is intentional and correct behaviour for TDD.
from assistant_app.tool_definitions import (
    AGENT_SYSTEM_PROMPT,
    TOOL_DEFINITIONS,
    build_tool_config,
    count_tool_definition_tokens,
)

# Spec Section 2 — the exact 9 tool names that must be present.
_EXPECTED_TOOL_NAMES = {
    "get_calendar_events",
    "get_task_lists",
    "get_tasks",
    "get_meeting_documents",
    "get_grocery_lists",
    "propose_calendar_event",
    "propose_task_update",
    "propose_task_complete",
    "propose_grocery_items",
}

# Tools scoped to google_calendar / microsoft_calendar only.
_CALENDAR_TOOLS = {"get_calendar_events", "propose_calendar_event"}

# Tools that must NOT appear when only google_calendar is connected.
_TASK_TOOLS = {
    "get_task_lists",
    "get_tasks",
    "propose_task_update",
    "propose_task_complete",
}

# Tools that must NOT appear when only google_calendar is connected.
_GROCERY_TOOLS = {"propose_grocery_items"}

# Read tools that appear in a full (no-filter) config.
_READ_TOOLS = {
    "get_task_lists",
    "get_tasks",
    "get_calendar_events",
    "get_meeting_documents",
    "get_grocery_lists",
}

# Write-proposal tools that need real IDs in their input schemas.
_WRITE_PROPOSAL_TOOLS_NEEDING_IDS = {
    "propose_task_update",
    "propose_task_complete",
}


def _tool_name(tool_def: dict) -> str:
    """Extract the tool name from the Bedrock toolSpec format."""
    return tool_def["toolSpec"]["name"]


def _tool_description(tool_def: dict) -> str:
    return tool_def["toolSpec"]["description"]


def _tool_input_schema(tool_def: dict) -> dict:
    return tool_def["toolSpec"]["inputSchema"]["json"]


class TestToolDefinitionsCount(unittest.TestCase):
    """AC-01: TOOL_DEFINITIONS has exactly 9 entries."""

    def test_tool_definitions_has_exactly_nine_entries(self) -> None:
        """AC-01: TOOL_DEFINITIONS must export exactly 9 tool definitions."""
        self.assertEqual(
            len(TOOL_DEFINITIONS),
            9,
            msg=f"Expected exactly 9 tool definitions, got {len(TOOL_DEFINITIONS)}",
        )


class TestToolDefinitionsStructure(unittest.TestCase):
    """AC-02: Each tool has the required Bedrock-format fields."""

    def test_each_tool_has_required_bedrock_fields(self) -> None:
        """AC-02: Each tool dict must have the toolSpec nesting required by Bedrock."""
        for tool_def in TOOL_DEFINITIONS:
            with self.subTest(tool=tool_def):
                self.assertIn(
                    "toolSpec",
                    tool_def,
                    msg="Each tool definition must have a 'toolSpec' key at the top level.",
                )
                spec = tool_def["toolSpec"]
                self.assertIn("name", spec, msg="toolSpec must have 'name'")
                self.assertIn("description", spec, msg="toolSpec must have 'description'")
                self.assertIn("inputSchema", spec, msg="toolSpec must have 'inputSchema'")
                self.assertIn(
                    "json",
                    spec["inputSchema"],
                    msg="toolSpec.inputSchema must have a 'json' key (Bedrock format).",
                )

    def test_each_tool_name_is_non_empty(self) -> None:
        """AC-02: Every tool name must be a non-empty string."""
        for tool_def in TOOL_DEFINITIONS:
            name = _tool_name(tool_def)
            with self.subTest(tool_name=name):
                self.assertIsInstance(name, str)
                self.assertGreater(len(name.strip()), 0, msg="Tool name must not be empty.")

    def test_each_tool_description_is_non_empty(self) -> None:
        """AC-02: Every tool description must be a non-empty string."""
        for tool_def in TOOL_DEFINITIONS:
            name = _tool_name(tool_def)
            desc = _tool_description(tool_def)
            with self.subTest(tool_name=name):
                self.assertIsInstance(desc, str)
                self.assertGreater(
                    len(desc.strip()), 0, msg=f"Tool '{name}' description must not be empty."
                )

    def test_each_tool_input_schema_is_non_empty(self) -> None:
        """AC-02: Every tool inputSchema must be a non-empty dict."""
        for tool_def in TOOL_DEFINITIONS:
            name = _tool_name(tool_def)
            schema = _tool_input_schema(tool_def)
            with self.subTest(tool_name=name):
                self.assertIsInstance(schema, dict)
                self.assertGreater(
                    len(schema), 0, msg=f"Tool '{name}' inputSchema must not be empty."
                )

    def test_tool_names_are_unique(self) -> None:
        """Every tool name must appear exactly once in TOOL_DEFINITIONS."""
        names = [_tool_name(t) for t in TOOL_DEFINITIONS]
        self.assertEqual(
            len(names),
            len(set(names)),
            msg=f"Duplicate tool names found: {[n for n in names if names.count(n) > 1]}",
        )

    def test_all_expected_tool_names_present(self) -> None:
        """The exact set of 9 named tools from the spec must all be present."""
        actual_names = {_tool_name(t) for t in TOOL_DEFINITIONS}
        self.assertEqual(
            actual_names,
            _EXPECTED_TOOL_NAMES,
            msg=(
                f"Missing tools: {_EXPECTED_TOOL_NAMES - actual_names}. "
                f"Extra tools: {actual_names - _EXPECTED_TOOL_NAMES}."
            ),
        )


class TestToolDefinitionsSchemaValidity(unittest.TestCase):
    """Each tool's inputSchema must be a structurally valid JSON Schema object."""

    def test_each_tool_input_schema_is_valid_json_schema(self) -> None:
        """AC-02 / Extra: inputSchema must have 'type': 'object' and 'properties'."""
        for tool_def in TOOL_DEFINITIONS:
            name = _tool_name(tool_def)
            schema = _tool_input_schema(tool_def)
            with self.subTest(tool_name=name):
                self.assertEqual(
                    schema.get("type"),
                    "object",
                    msg=f"Tool '{name}' inputSchema must have type=object.",
                )
                self.assertIn(
                    "properties",
                    schema,
                    msg=f"Tool '{name}' inputSchema must have a 'properties' key.",
                )
                self.assertIsInstance(
                    schema["properties"],
                    dict,
                    msg=f"Tool '{name}' inputSchema.properties must be a dict.",
                )

    def test_write_proposal_tools_have_list_id_or_equivalent_required_fields(self) -> None:
        """AC-02 / Extra: propose_task_update and propose_task_complete must require
        list_id and task_id in their inputSchema so the LLM cannot submit without them."""
        for tool_def in TOOL_DEFINITIONS:
            name = _tool_name(tool_def)
            if name not in _WRITE_PROPOSAL_TOOLS_NEEDING_IDS:
                continue
            schema = _tool_input_schema(tool_def)
            with self.subTest(tool_name=name):
                required_fields = schema.get("required", [])
                self.assertIn(
                    "list_id",
                    required_fields,
                    msg=f"Tool '{name}' must require 'list_id'.",
                )
                self.assertIn(
                    "task_id",
                    required_fields,
                    msg=f"Tool '{name}' must require 'task_id'.",
                )

    def test_propose_calendar_event_requires_title_start_end(self) -> None:
        """propose_calendar_event must require title, start, and end per spec Section 2.3."""
        tool_def = next(
            (t for t in TOOL_DEFINITIONS if _tool_name(t) == "propose_calendar_event"), None
        )
        self.assertIsNotNone(tool_def, "propose_calendar_event must be in TOOL_DEFINITIONS")
        schema = _tool_input_schema(tool_def)
        required = schema.get("required", [])
        for field in ("title", "start", "end"):
            self.assertIn(
                field,
                required,
                msg=f"propose_calendar_event must require '{field}'.",
            )

    def test_get_tasks_requires_list_id(self) -> None:
        """get_tasks must require list_id per spec Section 2.2."""
        tool_def = next(
            (t for t in TOOL_DEFINITIONS if _tool_name(t) == "get_tasks"), None
        )
        self.assertIsNotNone(tool_def, "get_tasks must be in TOOL_DEFINITIONS")
        schema = _tool_input_schema(tool_def)
        required = schema.get("required", [])
        self.assertIn("list_id", required, msg="get_tasks must require 'list_id'.")

    def test_propose_grocery_items_requires_list_name_and_items(self) -> None:
        """propose_grocery_items must require list_name and items per spec Section 2.3."""
        tool_def = next(
            (t for t in TOOL_DEFINITIONS if _tool_name(t) == "propose_grocery_items"), None
        )
        self.assertIsNotNone(tool_def, "propose_grocery_items must be in TOOL_DEFINITIONS")
        schema = _tool_input_schema(tool_def)
        required = schema.get("required", [])
        for field in ("list_name", "items"):
            self.assertIn(
                field,
                required,
                msg=f"propose_grocery_items must require '{field}'.",
            )


class TestTokenBudget(unittest.TestCase):
    """AC-03: count_tool_definition_tokens() returns ≤ 1500."""

    def test_count_tool_definition_tokens_within_budget(self) -> None:
        """AC-03: Combined tool definitions must not exceed 1500 tokens (CI gate)."""
        count = count_tool_definition_tokens()
        self.assertIsInstance(count, int, msg="count_tool_definition_tokens() must return int.")
        self.assertGreater(count, 0, msg="Token count must be positive.")
        self.assertLessEqual(
            count,
            1500,
            msg=(
                f"Tool definitions exceed the 1500-token budget: got {count} tokens. "
                "Trim descriptions to stay within budget."
            ),
        )

    def test_count_tool_definition_tokens_returns_positive_integer(self) -> None:
        """count_tool_definition_tokens() must return a positive integer."""
        count = count_tool_definition_tokens()
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)


class TestBuildToolConfig(unittest.TestCase):
    """AC-04: build_tool_config filters tools by connected provider."""

    def _names_in_config(self, config: dict) -> set[str]:
        """Extract tool names from a toolConfig dict."""
        tools_list = config.get("tools", [])
        return {_tool_name(t) for t in tools_list}

    # --- google_calendar filter ---

    def test_build_tool_config_google_calendar_includes_calendar_tools(self) -> None:
        """AC-04: google_calendar filter must include get_calendar_events and
        propose_calendar_event."""
        config = build_tool_config(["google_calendar"])
        names = self._names_in_config(config)
        self.assertIn(
            "get_calendar_events",
            names,
            msg="google_calendar config must include get_calendar_events.",
        )
        self.assertIn(
            "propose_calendar_event",
            names,
            msg="google_calendar config must include propose_calendar_event.",
        )

    def test_build_tool_config_google_calendar_excludes_task_tools(self) -> None:
        """AC-04: google_calendar filter must NOT include task tools."""
        config = build_tool_config(["google_calendar"])
        names = self._names_in_config(config)
        for tool_name in ("get_task_lists", "get_tasks", "propose_task_update", "propose_task_complete"):
            self.assertNotIn(
                tool_name,
                names,
                msg=f"google_calendar config must NOT include '{tool_name}'.",
            )

    def test_build_tool_config_google_calendar_excludes_grocery_tools(self) -> None:
        """AC-04: google_calendar filter must NOT include propose_grocery_items."""
        config = build_tool_config(["google_calendar"])
        names = self._names_in_config(config)
        self.assertNotIn(
            "propose_grocery_items",
            names,
            msg="google_calendar config must NOT include propose_grocery_items.",
        )

    # --- google_tasks filter ---

    def test_build_tool_config_google_tasks_includes_task_tools(self) -> None:
        """google_tasks filter must include task-related tools."""
        config = build_tool_config(["google_tasks"])
        names = self._names_in_config(config)
        for tool_name in ("get_task_lists", "get_tasks", "propose_task_update", "propose_task_complete"):
            self.assertIn(
                tool_name,
                names,
                msg=f"google_tasks config must include '{tool_name}'.",
            )

    def test_build_tool_config_google_tasks_excludes_calendar_tools(self) -> None:
        """google_tasks filter must NOT include calendar tools."""
        config = build_tool_config(["google_tasks"])
        names = self._names_in_config(config)
        self.assertNotIn(
            "get_calendar_events",
            names,
            msg="google_tasks config must NOT include get_calendar_events.",
        )
        self.assertNotIn(
            "propose_calendar_event",
            names,
            msg="google_tasks config must NOT include propose_calendar_event.",
        )

    def test_get_meeting_documents_in_google_drive_config(self) -> None:
        """get_meeting_documents is a google_drive tool; it must appear in that config."""
        config = build_tool_config(["google_drive"])
        names = self._names_in_config(config)
        self.assertIn(
            "get_meeting_documents",
            names,
            msg="google_drive config must include get_meeting_documents.",
        )

    def test_get_grocery_lists_in_google_tasks_config(self) -> None:
        """get_grocery_lists uses task providers; it must appear in google_tasks config."""
        config = build_tool_config(["google_tasks"])
        names = self._names_in_config(config)
        self.assertIn(
            "get_grocery_lists",
            names,
            msg="google_tasks config must include get_grocery_lists.",
        )

    def test_propose_grocery_items_in_google_tasks_config(self) -> None:
        """propose_grocery_items uses task providers; must appear in google_tasks config."""
        config = build_tool_config(["google_tasks"])
        names = self._names_in_config(config)
        self.assertIn(
            "propose_grocery_items",
            names,
            msg="google_tasks config must include propose_grocery_items.",
        )

    def test_propose_calendar_event_in_google_calendar_config(self) -> None:
        """propose_calendar_event must appear in google_calendar config."""
        config = build_tool_config(["google_calendar"])
        names = self._names_in_config(config)
        self.assertIn(
            "propose_calendar_event",
            names,
            msg="google_calendar config must include propose_calendar_event.",
        )

    # --- empty / None → all tools ---

    def test_build_tool_config_empty_list_returns_all_tools(self) -> None:
        """AC-04 / Extra: build_tool_config([]) must return all 9 tools."""
        config = build_tool_config([])
        names = self._names_in_config(config)
        self.assertEqual(
            len(names),
            9,
            msg=f"build_tool_config([]) must return all 9 tools, got {len(names)}.",
        )

    def test_build_tool_config_none_returns_all_tools(self) -> None:
        """AC-04 / Extra: build_tool_config(None) must return all 9 tools."""
        config = build_tool_config(None)
        names = self._names_in_config(config)
        self.assertEqual(
            len(names),
            9,
            msg=f"build_tool_config(None) must return all 9 tools, got {len(names)}.",
        )

    # --- full config includes required read tools ---

    def test_full_tool_config_includes_read_tools(self) -> None:
        """AC-04 / Extra: Full config (no filter) must include all 5 read tools."""
        config = build_tool_config(None)
        names = self._names_in_config(config)
        for tool_name in _READ_TOOLS:
            self.assertIn(
                tool_name,
                names,
                msg=f"Full tool config must include read tool '{tool_name}'.",
            )

    def test_build_tool_config_returns_dict_with_tools_key(self) -> None:
        """build_tool_config must return a dict with a 'tools' key (Bedrock toolConfig format)."""
        config = build_tool_config(None)
        self.assertIsInstance(config, dict)
        self.assertIn("tools", config, msg="build_tool_config result must have a 'tools' key.")
        self.assertIsInstance(config["tools"], list)


class TestAgentSystemPrompt(unittest.TestCase):
    """AC-05: AGENT_SYSTEM_PROMPT is non-empty and contains 'DATA BEFORE WRITES'."""

    def test_agent_system_prompt_is_non_empty(self) -> None:
        """AC-05: AGENT_SYSTEM_PROMPT must not be an empty string."""
        self.assertIsInstance(AGENT_SYSTEM_PROMPT, str)
        self.assertGreater(
            len(AGENT_SYSTEM_PROMPT.strip()),
            0,
            msg="AGENT_SYSTEM_PROMPT must not be empty.",
        )

    def test_agent_system_prompt_contains_data_before_writes(self) -> None:
        """AC-05: The literal phrase 'DATA BEFORE WRITES' must appear in the system prompt."""
        self.assertIn(
            "DATA BEFORE WRITES",
            AGENT_SYSTEM_PROMPT,
            msg="AGENT_SYSTEM_PROMPT must contain the phrase 'DATA BEFORE WRITES'.",
        )

    def test_agent_system_prompt_contains_proposal_language(self) -> None:
        """System prompt must make clear that write tools create proposals, not executions.
        The word 'proposal' (or 'proposals') must appear."""
        self.assertIn(
            "proposal",
            AGENT_SYSTEM_PROMPT.lower(),
            msg="AGENT_SYSTEM_PROMPT must mention 'proposal' to clarify write intent.",
        )

    def test_agent_system_prompt_mentions_never_invent_ids(self) -> None:
        """System prompt must tell the LLM never to invent or guess IDs."""
        prompt_lower = AGENT_SYSTEM_PROMPT.lower()
        has_invent = "invent" in prompt_lower
        has_guess = "guess" in prompt_lower
        self.assertTrue(
            has_invent or has_guess,
            msg=(
                "AGENT_SYSTEM_PROMPT must instruct the LLM to never invent or guess IDs. "
                "Expected 'invent' or 'guess' in the prompt text."
            ),
        )


if __name__ == "__main__":
    unittest.main()
