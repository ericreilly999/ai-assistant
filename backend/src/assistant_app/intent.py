from __future__ import annotations

import re
from dataclasses import dataclass

WRITE_HINTS = (
    "add",
    "create",
    "update",
    "schedule",
    "book",
    "move",
    "cancel",
    "plan",
    "remind",
    "complete",
    "finish",
    "done",
    "check off",
    "rename",
    "edit",
)

META_HINTS = (
    "which",
    "what can you",
    "what do you",
    "how about",
    "are you",
    "do you",
    "can you",
    "what providers",
    "what integrations",
)


@dataclass(frozen=True)
class IntentClassification:
    domain: str
    operation: str
    requires_confirmation: bool


def classify_message(message: str) -> IntentClassification:
    normalized = message.strip().lower()
    requires_confirmation = any(token in normalized for token in WRITE_HINTS)

    if not requires_confirmation and any(hint in normalized for hint in META_HINTS):
        return IntentClassification("general", "read", False)

    if any(token in normalized for token in ("grocery", "groceries", "dinner", "meal")):
        return IntentClassification("grocery", "write" if requires_confirmation else "read", requires_confirmation)
    if any(token in normalized for token in ("meeting", "prepare me", "agenda", "architecture review")):
        return IntentClassification("meeting_prep", "read", False)
    if any(token in normalized for token in ("trip", "travel", "weekend")):
        return IntentClassification("travel", "write" if requires_confirmation else "read", requires_confirmation)
    if any(token in normalized for token in ("calendar", "schedule", "day look like", "tomorrow", "today", "event", "reminder")):
        return IntentClassification("calendar", "write" if requires_confirmation else "read", requires_confirmation)
    if any(token in normalized for token in ("task", "tasks", "todo", "to-do", "to do")):
        return IntentClassification("tasks", "write" if requires_confirmation else "read", requires_confirmation)
    return IntentClassification("general", "write" if requires_confirmation else "read", requires_confirmation)


def extract_grocery_items(message: str) -> list[str]:
    normalized = message.strip()
    if "add" in normalized.lower():
        _, tail = re.split(r"\badd\b", normalized, maxsplit=1, flags=re.IGNORECASE)
        tail = tail.replace(" to my grocery list", "")
        tail = tail.replace(" to the grocery list", "")
        tail = tail.replace(" and ", ",")
        candidates = [part.strip(" .") for part in tail.split(",")]
        return [item for item in candidates if item]

    if "plan dinners" in normalized.lower() or "dinner" in normalized.lower():
        return [
            "chicken",
            "bell peppers",
            "soy sauce",
            "pasta",
            "garlic bread",
            "taco shells",
            "ground beef",
        ]

    return ["milk", "eggs", "spinach"]
