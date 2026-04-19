from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from assistant_app.dev_store import DevTokenStore


class DevTokenStoreTests(unittest.TestCase):
    """File-backed store (no OAUTH_TOKEN_TABLE set)."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store_path = os.path.join(self._tmpdir, "tokens.json")
        # Ensure DynamoDB path is not taken during file-mode tests.
        os.environ.pop("OAUTH_TOKEN_TABLE", None)
        self.store = DevTokenStore(self._store_path)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("OAUTH_TOKEN_TABLE", None)

    def test_load_returns_empty_dict_when_file_missing(self) -> None:
        self.assertEqual(self.store.load(), {})

    def test_get_tokens_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.store.get_tokens("google"))

    def test_set_and_get_tokens_roundtrip(self) -> None:
        self.store.set_tokens("google", {"access_token": "tok-abc", "expires_in": 3600})
        tokens = self.store.get_tokens("google")
        self.assertIsNotNone(tokens)
        self.assertEqual(tokens["access_token"], "tok-abc")  # type: ignore[index]

    def test_save_creates_parent_directories(self) -> None:
        deep_path = os.path.join(self._tmpdir, "sub", "dir", "tokens.json")
        store = DevTokenStore(deep_path)
        store.set_tokens("plaid", {"access_token": "plaid-tok"})
        self.assertTrue(Path(deep_path).exists())

    def test_clear_tokens_removes_provider(self) -> None:
        self.store.set_tokens("google", {"access_token": "tok"})
        self.store.clear_tokens("google")
        self.assertIsNone(self.store.get_tokens("google"))

    def test_clear_tokens_nonexistent_key_is_no_op(self) -> None:
        self.store.clear_tokens("nonexistent")  # should not raise

    def test_merge_tokens_updates_existing_keys(self) -> None:
        self.store.set_tokens("google", {"access_token": "old-tok", "scope": "email"})
        self.store.merge_tokens("google", {"access_token": "new-tok"})
        tokens = self.store.get_tokens("google")
        self.assertEqual(tokens["access_token"], "new-tok")  # type: ignore[index]
        self.assertEqual(tokens["scope"], "email")  # type: ignore[index]

    def test_merge_tokens_creates_provider_if_absent(self) -> None:
        self.store.merge_tokens("microsoft", {"access_token": "ms-tok"})
        tokens = self.store.get_tokens("microsoft")
        self.assertEqual(tokens["access_token"], "ms-tok")  # type: ignore[index]

    def test_plaid_status_no_token(self) -> None:
        status = self.store.plaid_status()
        self.assertFalse(status["has_access_token"])

    def test_plaid_status_with_token(self) -> None:
        self.store.set_tokens("plaid", {"access_token": "plaid-tok", "institution_id": "ins_123"})
        status = self.store.plaid_status()
        self.assertTrue(status["has_access_token"])
        self.assertEqual(status["institution_id"], "ins_123")

    def test_expires_at_returns_none_when_no_tokens(self) -> None:
        self.assertIsNone(self.store.expires_at("google"))

    def test_expires_at_returns_value_when_set(self) -> None:
        self.store.set_tokens("google", {"access_token": "tok", "expires_at": "2026-01-01T00:00:00+00:00"})
        self.assertEqual(self.store.expires_at("google"), "2026-01-01T00:00:00+00:00")

    def test_load_handles_malformed_file(self) -> None:
        Path(self._store_path).write_text("not valid json", encoding="utf-8")
        self.assertEqual(self.store.load(), {})

    def test_load_handles_empty_file(self) -> None:
        Path(self._store_path).write_text("", encoding="utf-8")
        self.assertEqual(self.store.load(), {})

    def test_multiple_providers_stored_independently(self) -> None:
        self.store.set_tokens("google", {"access_token": "g-tok"})
        self.store.set_tokens("microsoft", {"access_token": "ms-tok"})
        self.store.set_tokens("plaid", {"access_token": "p-tok"})
        self.assertEqual(self.store.get_tokens("google")["access_token"], "g-tok")  # type: ignore[index]
        self.assertEqual(self.store.get_tokens("microsoft")["access_token"], "ms-tok")  # type: ignore[index]
        self.assertEqual(self.store.get_tokens("plaid")["access_token"], "p-tok")  # type: ignore[index]


def _make_dynamodb_store(mock_table: MagicMock) -> DevTokenStore:
    """Construct a DevTokenStore wired to a mock DynamoDB Table."""
    with patch.dict(os.environ, {"OAUTH_TOKEN_TABLE": "ai-assistant-dev-tokens"}), patch("boto3.resource") as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        store = DevTokenStore("/tmp/unused.json")
    return store


class DynamoDBTokenStoreTests(unittest.TestCase):
    """DynamoDB-backed store (OAUTH_TOKEN_TABLE set, boto3 mocked)."""

    def setUp(self) -> None:
        self._table = MagicMock()
        self._store = _make_dynamodb_store(self._table)

    # ------------------------------------------------------------------ get_tokens

    def test_get_tokens_returns_none_when_item_missing(self) -> None:
        self._table.get_item.return_value = {}
        self.assertIsNone(self._store.get_tokens("google", user_id="user-abc"))
        # Partition key attribute name must be "pk", value is composite {user_id}#{provider}
        self._table.get_item.assert_called_once_with(Key={"pk": "user-abc#google"})

    def test_get_tokens_returns_dict_when_item_exists(self) -> None:
        tokens = {"access_token": "ddb-tok", "expires_in": 3600}
        self._table.get_item.return_value = {"Item": {"pk": "user-abc#google", "tokens": json.dumps(tokens)}}
        result = self._store.get_tokens("google", user_id="user-abc")
        self.assertEqual(result, tokens)

    def test_get_tokens_default_user_id_is_local(self) -> None:
        """When user_id is omitted the key falls back to 'local#<provider>'."""
        self._table.get_item.return_value = {}
        self._store.get_tokens("google")
        self._table.get_item.assert_called_once_with(Key={"pk": "local#google"})

    # ------------------------------------------------------------------ set_tokens

    def test_set_tokens_calls_put_item_with_json_serialised_tokens(self) -> None:
        tokens = {"access_token": "new-tok"}
        self._store.set_tokens("microsoft", tokens, user_id="user-abc")
        self._table.put_item.assert_called_once_with(
            Item={"pk": "user-abc#microsoft", "tokens": json.dumps(tokens)}
        )

    # ------------------------------------------------------------------ clear_tokens

    def test_clear_tokens_calls_delete_item(self) -> None:
        self._store.clear_tokens("google", user_id="user-abc")
        self._table.delete_item.assert_called_once_with(Key={"pk": "user-abc#google"})

    # ------------------------------------------------------------------ merge_tokens

    def test_merge_tokens_merges_into_existing_tokens(self) -> None:
        existing = {"access_token": "old-tok", "scope": "email"}
        self._table.get_item.return_value = {"Item": {"pk": "user-abc#google", "tokens": json.dumps(existing)}}
        self._store.merge_tokens("google", {"access_token": "new-tok"}, user_id="user-abc")
        expected = {"access_token": "new-tok", "scope": "email"}
        self._table.put_item.assert_called_once_with(
            Item={"pk": "user-abc#google", "tokens": json.dumps(expected)}
        )

    def test_merge_tokens_creates_provider_if_absent(self) -> None:
        self._table.get_item.return_value = {}
        self._store.merge_tokens("microsoft", {"access_token": "ms-tok"}, user_id="user-abc")
        self._table.put_item.assert_called_once_with(
            Item={"pk": "user-abc#microsoft", "tokens": json.dumps({"access_token": "ms-tok"})}
        )

    # ------------------------------------------------------------------ plaid_status

    def test_plaid_status_no_token(self) -> None:
        self._table.get_item.return_value = {}
        status = self._store.plaid_status(user_id="user-abc")
        self.assertFalse(status["has_access_token"])
        self.assertIsNone(status["institution_id"])

    def test_plaid_status_with_token(self) -> None:
        plaid_tokens = {"access_token": "plaid-tok", "institution_id": "ins_123"}
        self._table.get_item.return_value = {"Item": {"pk": "user-abc#plaid", "tokens": json.dumps(plaid_tokens)}}
        status = self._store.plaid_status(user_id="user-abc")
        self.assertTrue(status["has_access_token"])
        self.assertEqual(status["institution_id"], "ins_123")

    # ------------------------------------------------------------------ expires_at

    def test_expires_at_returns_none_when_no_tokens(self) -> None:
        self._table.get_item.return_value = {}
        self.assertIsNone(self._store.expires_at("google", user_id="user-abc"))

    def test_expires_at_returns_value_when_set(self) -> None:
        tokens = {"access_token": "tok", "expires_at": "2026-01-01T00:00:00+00:00"}
        self._table.get_item.return_value = {"Item": {"pk": "user-abc#google", "tokens": json.dumps(tokens)}}
        self.assertEqual(self._store.expires_at("google", user_id="user-abc"), "2026-01-01T00:00:00+00:00")

    # ------------------------------------------------------------------ multi-user isolation

    def test_multi_user_isolation(self) -> None:
        """User A's get_tokens must NOT return user B's token record.

        The DynamoDB key for user-A#google and user-B#google are different pk values,
        so a lookup for user-A can never return the record written for user-B.
        This test proves that the two key values are distinct strings.
        """
        tokens_a = {"access_token": "tok-user-a"}
        tokens_b = {"access_token": "tok-user-b"}

        # Simulate DynamoDB returning user B's record for user B's key
        def side_effect(Key):  # noqa: N803
            if Key == {"pk": "user-B#google"}:
                return {"Item": {"pk": "user-B#google", "tokens": json.dumps(tokens_b)}}
            # Any other key (e.g. user-A#google) returns empty — no record
            return {}

        self._table.get_item.side_effect = side_effect

        result_a = self._store.get_tokens("google", user_id="user-A")
        result_b = self._store.get_tokens("google", user_id="user-B")

        # user-A's lookup returns None (no matching record)
        self.assertIsNone(result_a)
        # user-B's lookup returns only user-B's tokens
        self.assertEqual(result_b, tokens_b)
        # The two DynamoDB keys must be distinct strings
        key_a = self._store._ddb_key("user-A", "google")
        key_b = self._store._ddb_key("user-B", "google")
        self.assertNotEqual(key_a, key_b)

    # ------------------------------------------------------------------ TTL attribute

    def test_set_tokens_writes_expires_at_number_when_expires_in_present(self) -> None:
        """expires_in triggers a top-level integer expires_at for DynamoDB TTL."""
        import time as _time
        tokens = {"access_token": "tok", "expires_in": 3600}
        before = int(_time.time())
        self._store.set_tokens("google", tokens, user_id="user-abc")
        after = int(_time.time())

        call_args = self._table.put_item.call_args
        item = call_args[1]["Item"] if call_args[1] else call_args[0][0]["Item"]
        self.assertIn("expires_at", item)
        self.assertIsInstance(item["expires_at"], int)
        # expires_at must be approximately now + 3600 s
        self.assertGreaterEqual(item["expires_at"], before + 3600)
        self.assertLessEqual(item["expires_at"], after + 3600)

    def test_set_tokens_writes_expires_at_number_when_expires_at_is_int(self) -> None:
        """When expires_at is already an integer epoch, it is passed through as-is."""
        epoch = 1800000000
        tokens = {"access_token": "tok", "expires_at": epoch}
        self._store.set_tokens("google", tokens, user_id="user-abc")

        call_args = self._table.put_item.call_args
        item = call_args[1]["Item"] if call_args[1] else call_args[0][0]["Item"]
        self.assertEqual(item["expires_at"], epoch)

    def test_set_tokens_omits_expires_at_when_no_expiry(self) -> None:
        """When neither expires_in nor numeric expires_at is present, no TTL attribute."""
        tokens = {"access_token": "tok"}
        self._store.set_tokens("google", tokens, user_id="user-abc")

        call_args = self._table.put_item.call_args
        item = call_args[1]["Item"] if call_args[1] else call_args[0][0]["Item"]
        self.assertNotIn("expires_at", item)

    # ------------------------------------------------------------------ dispatch check

    def test_file_based_store_has_no_table(self) -> None:
        """When OAUTH_TOKEN_TABLE is absent, _table must be None."""
        os.environ.pop("OAUTH_TOKEN_TABLE", None)
        store = DevTokenStore("/tmp/some_path.json")
        self.assertIsNone(store._table)
