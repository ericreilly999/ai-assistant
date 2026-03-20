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


def build_action_proposal(
    provider: str,
    action_type: str,
    resource_type: str,
    payload: dict[str, Any],
    summary: str,
    ttl_minutes: int,
    now: datetime | None = None,
) -> ActionProposal:
    issued_at = now or datetime.now(timezone.utc)
    hashed_payload = payload_hash(payload)
    proposal_id_seed = f"{provider}:{action_type}:{hashed_payload}:{issued_at.isoformat()}"
    proposal_id = hashlib.sha1(proposal_id_seed.encode("utf-8")).hexdigest()[:16]
    expires_at = issued_at + timedelta(minutes=ttl_minutes)

    return ActionProposal(
        proposal_id=proposal_id,
        provider=provider,
        action_type=action_type,
        resource_type=resource_type,
        payload=payload,
        payload_hash=hashed_payload,
        summary=summary,
        risk_level="low",
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