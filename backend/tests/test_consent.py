from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from assistant_app.consent import build_action_proposal, payload_hash, validate_execute_request


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