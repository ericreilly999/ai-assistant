"""Tool definitions for the Phase 13 LLM Tool Use Orchestrator.

Contains:
- AGENT_SYSTEM_PROMPT: The system prompt injected on every Bedrock Converse call.
- TOOL_DEFINITIONS: All 9 tool schemas in Bedrock toolConfig format.
- build_tool_config: Returns a filtered toolConfig dict based on connected providers.
- count_tool_definition_tokens: Returns a token count estimate for the tool definitions.
"""
from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT: str = (
    "You are a personal AI assistant. You help the user manage their calendar, tasks, grocery lists, "
    "and meeting preparation. You have access to tools that can read data from connected providers "
    "(Google Calendar, Google Tasks, Microsoft Calendar, Microsoft To Do, Google Drive) and tools that "
    "can propose write actions for user approval.\n\n"
    "RULES YOU MUST FOLLOW:\n\n"
    "1. DATA BEFORE WRITES. You must NEVER call a write-proposal tool (propose_task_update, "
    "propose_task_complete) without first calling the corresponding read tools to obtain real IDs. "
    "Example: if the user says \"mark my dentist task as done\", you must:\n"
    "  Step 1 — call get_task_lists to get the list ID.\n"
    "  Step 2 — call get_tasks with that list ID to find the task and its ID.\n"
    "  Step 3 — only then call propose_task_complete with the real list_id and task_id.\n"
    "You must NEVER invent or guess a list_id or task_id.\n\n"
    "2. CONVERSATIONAL QUESTIONS. If the user asks a general question, capability question, or makes "
    "small talk, respond in plain text. Do not call any tools. Examples: \"what can you do?\", "
    "\"are you connected to my calendar?\", \"thanks\".\n\n"
    "3. OUT-OF-SCOPE REQUESTS. If the user asks for something you cannot help with (financial data, "
    "file deletion, browsing the web), respond in plain text explaining what you can do instead.\n\n"
    "4. AMBIGUOUS REQUESTS. If a request is ambiguous and you cannot proceed without clarification "
    "(e.g. \"update my task\" without specifying which task), ask a clarifying question in plain text "
    "before calling any tools.\n\n"
    "5. PROPOSALS, NOT EXECUTIONS. Write-proposal tools create a proposal for the user to review and "
    "approve. Tell the user what you proposed and that they must approve it before anything changes. "
    "Never imply the action has already happened.\n\n"
    "6. PROVIDER SELECTION. If the user has both Google and Microsoft providers connected, prefer "
    "Google Calendar for calendar operations and Google Tasks for task operations unless the user "
    "specifies otherwise. For grocery lists, use whichever task provider has a list named "
    "\"Groceries\" or similar.\n\n"
    "7. RESPONSE STYLE. Be concise and specific. Do not add disclaimers or preamble. Report what you "
    "found, what you proposed, and what the user should do next."
)

# ---------------------------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "toolSpec": {
            "name": "get_calendar_events",
            "description": (
                "Fetch calendar events for a date range. Use when the user asks about schedule, "
                "meetings, or free time. start and end must be ISO 8601 with timezone offset "
                "(e.g. 2026-04-18T09:00:00-04:00). Max 20 events returned."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "start": {
                            "type": "string",
                            "description": "Start of range, ISO 8601 with timezone.",
                        },
                        "end": {
                            "type": "string",
                            "description": "End of range, ISO 8601 with timezone.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["google_calendar", "microsoft_calendar"],
                            "description": "Calendar provider. Omit for first connected.",
                        },
                    },
                    "required": ["start", "end"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_task_lists",
            "description": (
                "Fetch all task list names and IDs. Call this BEFORE get_tasks, "
                "propose_task_update, or propose_task_complete — real list IDs required."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google_tasks", "microsoft_todo"],
                            "description": "Task provider. Omit for first connected.",
                        },
                    },
                    "required": [],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_tasks",
            "description": (
                "Fetch tasks in a list by list_id. Call get_task_lists first to get a real "
                "list_id — never guess. Returns up to 50 tasks. task id and list_id are "
                "required for propose_task_update and propose_task_complete."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "Task list ID from get_task_lists.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["google_tasks", "microsoft_todo"],
                            "description": "Task provider.",
                        },
                    },
                    "required": ["list_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_meeting_documents",
            "description": (
                "Fetch Google Drive documents for an upcoming meeting. Use when preparing "
                "for a meeting. Optional keyword filters by title. Returns up to 10 docs."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Optional keyword to filter documents by title.",
                        },
                    },
                    "required": [],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_grocery_lists",
            "description": (
                "Fetch grocery/shopping lists and current items. Use before proposing additions "
                "to show existing items. Returns list names, IDs, and items."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google_tasks", "microsoft_todo"],
                            "description": "Task provider.",
                        },
                    },
                    "required": [],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "propose_calendar_event",
            "description": (
                "Propose a new calendar event for user approval. Does NOT create immediately. "
                "Use when user asks to schedule or book an event. Datetimes must be ISO 8601 "
                "with timezone."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event title."},
                        "start": {
                            "type": "string",
                            "description": "Start datetime, ISO 8601 with timezone.",
                        },
                        "end": {
                            "type": "string",
                            "description": "End datetime, ISO 8601 with timezone.",
                        },
                        "location": {"type": "string", "description": "Location or meeting link."},
                        "notes": {"type": "string", "description": "Description or agenda."},
                        "reminder_minutes": {
                            "type": "integer",
                            "description": "Reminder lead time in minutes.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["google_calendar", "microsoft_calendar"],
                            "description": "Calendar provider. Omit for first connected.",
                        },
                    },
                    "required": ["title", "start", "end"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "propose_task_update",
            "description": (
                "Propose updating a task's title, due date, or notes for user approval. "
                "Does NOT update immediately. MUST provide list_id and task_id from a prior "
                "get_tasks call. Never invent or guess these IDs."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "Task list ID from get_task_lists.",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from get_tasks.",
                        },
                        "updates": {
                            "type": "object",
                            "description": "Fields to update: title, due (ISO date), notes.",
                            "properties": {
                                "title": {"type": "string"},
                                "due": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["google_tasks", "microsoft_todo"],
                            "description": "Task provider.",
                        },
                    },
                    "required": ["list_id", "task_id", "updates"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "propose_task_complete",
            "description": (
                "Propose marking a task complete for user approval. Does NOT complete immediately. "
                "MUST provide list_id and task_id from a prior get_tasks call. "
                "Never invent or guess these IDs."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "Task list ID from get_task_lists.",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from get_tasks.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["google_tasks", "microsoft_todo"],
                            "description": "Task provider.",
                        },
                    },
                    "required": ["list_id", "task_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "propose_grocery_items",
            "description": (
                "Propose adding items to a grocery/shopping list for user approval. "
                "Does NOT add immediately. Provide list_name (e.g. Groceries) and items."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "list_name": {
                            "type": "string",
                            "description": "Grocery or shopping list name (e.g. Groceries).",
                        },
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Item names to add.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["google_tasks", "microsoft_todo"],
                            "description": "Task provider. Omit for first connected.",
                        },
                    },
                    "required": ["list_name", "items"],
                }
            },
        }
    },
]

# ---------------------------------------------------------------------------
# Provider → Tool mapping
# ---------------------------------------------------------------------------

# Maps each provider to the set of tool names that apply to it.
_PROVIDER_TOOL_MAP: dict[str, set[str]] = {
    "google_calendar": {"get_calendar_events", "propose_calendar_event"},
    "microsoft_calendar": {"get_calendar_events", "propose_calendar_event"},
    "google_tasks": {
        "get_task_lists",
        "get_tasks",
        "propose_task_update",
        "propose_task_complete",
        "propose_grocery_items",
        "get_grocery_lists",
    },
    "microsoft_todo": {
        "get_task_lists",
        "get_tasks",
        "propose_task_update",
        "propose_task_complete",
        "propose_grocery_items",
        "get_grocery_lists",
    },
    "google_drive": {"get_meeting_documents"},
}


def build_tool_config(connected_providers: list[str] | None = None) -> dict:
    """Return a Bedrock toolConfig dict filtered to tools applicable to the given providers.

    If connected_providers is None or empty, all tools are included.
    """
    if not connected_providers:
        return {"tools": list(TOOL_DEFINITIONS)}

    # Collect all tool names applicable to the given providers
    applicable_tool_names: set[str] = set()
    for provider in connected_providers:
        applicable_tool_names.update(_PROVIDER_TOOL_MAP.get(provider, set()))

    filtered = [
        tool_def
        for tool_def in TOOL_DEFINITIONS
        if tool_def["toolSpec"]["name"] in applicable_tool_names
    ]
    return {"tools": filtered}


def count_tool_definition_tokens() -> int:
    """Return a token count estimate for all tool definitions.

    Uses len(json.dumps(TOOL_DEFINITIONS).encode()) // 4 as an approximation
    (4 bytes ≈ 1 token). Must return <= 1500.
    """
    return len(json.dumps(TOOL_DEFINITIONS).encode()) // 4
