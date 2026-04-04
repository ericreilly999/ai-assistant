from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from assistant_app.models import ActionProposal


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def payload_hash(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8"))
    return digest.hexdigest()


_HIGH_RISK_ACTION_TYPES = {
    "delete_event",
    "delete_task",
    "cancel_event",
    "bulk_delete",
}

_MEDIUM_RISK_ACTION_TYPES = {
    "create_calendar_event",
    "update_task",
    "complete_task",
    "upsert_grocery_items",
}

_HIGH_RISK_MESSAGE_TOKENS = (
    "delete",
    "remove",
    "cancel all",
    "clear",
    "wipe",
    "drop",
)

_MEDIUM_RISK_MESSAGE_TOKENS = (
    "update",
    "change",
    "reschedule",
    "move",
    "edit",
    "rename",
)


def classify_risk_level(action_type: str, payload: dict[str, Any], message: str = "") -> str:
    """Classify the risk level of a proposed action.

    Returns 'high', 'medium', or 'low'.
    """
    if action_type in _HIGH_RISK_ACTION_TYPES:
        return "high"

    normalized_message = message.strip().lower()
    if any(token in normalized_message for token in _HIGH_RISK_MESSAGE_TOKENS):
        return "high"

    items = payload.get("items") or []
    if isinstance(items, list) and len(items) > 10:
        return "medium"

    if action_type in _MEDIUM_RISK_ACTION_TYPES:
        return "medium"

    if any(token in normalized_message for token in _MEDIUM_RISK_MESSAGE_TOKENS):
        return "medium"

    return "low"


def build_action_proposal(
    provider: str,
    action_type: str,
    resource_type: str,
    payload: dict[str, Any],
    summary: str,
    ttl_minutes: int,
    now: datetime | None = None,
    message: str = "",
) -> ActionProposal:
    issued_at = now or datetime.now(timezone.utc)
    hashed_payload = payload_hash(payload)
    proposal_id_seed = f"{provider}:{action_type}:{hashed_payload}:{issued_at.isoformat()}"
    proposal_id = hashlib.sha1(proposal_id_seed.encode("utf-8")).hexdigest()[:16]
    expires_at = issued_at + timedelta(minutes=ttl_minutes)
    risk = classify_risk_level(action_type, payload, message)

    return ActionProposal(
        proposal_id=proposal_id,
        provider=provider,
        action_type=action_type,
        resource_type=resource_type,
        payload=payload,
        payload_hash=hashed_payload,
        summary=summary,
        risk_level=risk,
        requires_confirmation=True,
        expires_at=expires_at.isoformat(),
    )


def validate_execute_request(request_payload: dict[str, Any], now: datetime | None = None) -> tuple[bool, str]:
    current_time = now or datetime.now(timezone.utc)

    if request_payload.get("approved") is not True:
        return False, "Explicit approval is required before executing a write."

    payload = request_payload.get("payload") or {}
    submitted_hash = request_payload.get("payload_hash", "")
    computed_hash = payload_hash(payload)
    if submitted_hash != computed_hash:
        return False, "Payload hash mismatch. The action must be replanned before execution."

    expires_at = request_payload.get("expires_at")
    if expires_at:
        expiry = datetime.fromisoformat(expires_at)
        if expiry < current_time:
            return False, "The proposal has expired. Re-run the planning step."

    return True, "ok"
