from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from assistant_app.consent import (
    build_action_proposal,
    classify_risk_level,
    payload_hash,
    validate_execute_request,
)


class ConsentTests(unittest.TestCase):
    def test_build_action_proposal_generates_hash_and_expiry(self) -> None:
        proposal = build_action_proposal(
            provider="google_tasks",
            action_type="upsert_grocery_items",
            resource_type="task_list",
            payload={"list_name": "Groceries", "items": ["milk"]},
            summary="Add milk",
            ttl_minutes=15,
            now=datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(proposal.proposal_id)
        self.assertEqual(proposal.payload_hash, payload_hash({"list_name": "Groceries", "items": ["milk"]}))
        self.assertTrue(proposal.requires_confirmation)
        self.assertIn("2026-03-16T12:15:00", proposal.expires_at)

    def test_build_action_proposal_approved_false_rejected(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        is_valid, message = validate_execute_request(
            {
                "approved": False,
                "payload_hash": payload_hash(payload),
                "payload": payload,
            }
        )
        self.assertFalse(is_valid)
        self.assertIn("approval", message)

    def test_validate_execute_request_rejects_mismatched_payload_hash(self) -> None:
        is_valid, message = validate_execute_request(
            {
                "approved": True,
                "payload_hash": "incorrect",
                "payload": {"value": 1},
                "expires_at": "2026-03-16T12:15:00+00:00",
            },
            now=datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(is_valid)
        self.assertIn("Payload hash mismatch", message)

    def test_validate_execute_request_rejects_expired_proposal(self) -> None:
        expired_at = datetime(2026, 3, 16, 11, 0, tzinfo=timezone.utc)
        is_valid, message = validate_execute_request(
            {
                "approved": True,
                "payload_hash": payload_hash({"value": 1}),
                "payload": {"value": 1},
                "expires_at": expired_at.isoformat(),
            },
            now=expired_at + timedelta(minutes=30),
        )
        self.assertFalse(is_valid)
        self.assertIn("expired", message)

    def test_validate_execute_request_accepts_valid(self) -> None:
        payload = {"list_name": "Groceries", "items": ["milk"]}
        future = datetime.now(timezone.utc) + timedelta(minutes=10)
        is_valid, message = validate_execute_request(
            {
                "approved": True,
                "payload_hash": payload_hash(payload),
                "payload": payload,
                "expires_at": future.isoformat(),
            }
        )
        self.assertTrue(is_valid)
        self.assertEqual(message, "ok")

    def test_validate_execute_request_no_expires_at_still_valid(self) -> None:
        payload = {"items": ["milk"]}
        is_valid, _ = validate_execute_request(
            {
                "approved": True,
                "payload_hash": payload_hash(payload),
                "payload": payload,
            }
        )
        self.assertTrue(is_valid)


class RiskLevelTests(unittest.TestCase):
    def test_delete_action_is_high_risk(self) -> None:
        level = classify_risk_level("delete_event", {})
        self.assertEqual(level, "high")

    def test_cancel_event_action_is_high_risk(self) -> None:
        level = classify_risk_level("cancel_event", {})
        self.assertEqual(level, "high")

    def test_delete_message_token_is_high_risk(self) -> None:
        level = classify_risk_level("update_task", {}, message="delete all my tasks")
        self.assertEqual(level, "high")

    def test_upsert_grocery_items_is_medium_risk(self) -> None:
        level = classify_risk_level("upsert_grocery_items", {"items": ["milk"]})
        self.assertEqual(level, "medium")

    def test_create_calendar_event_is_medium_risk(self) -> None:
        level = classify_risk_level("create_calendar_event", {})
        self.assertEqual(level, "medium")

    def test_large_item_list_is_medium_risk(self) -> None:
        items = [f"item_{i}" for i in range(15)]
        level = classify_risk_level("upsert_grocery_items", {"items": items})
        self.assertEqual(level, "medium")

    def test_unknown_read_action_is_low_risk(self) -> None:
        level = classify_risk_level("read_events", {})
        self.assertEqual(level, "low")

    def test_proposal_risk_level_embedded(self) -> None:
        proposal = build_action_proposal(
            provider="google_tasks",
            action_type="upsert_grocery_items",
            resource_type="task_list",
            payload={"items": ["milk"]},
            summary="Add milk",
            ttl_minutes=15,
        )
        self.assertIn(proposal.risk_level, {"low", "medium", "high"})
