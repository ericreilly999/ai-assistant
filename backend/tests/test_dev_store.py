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
        self.assertIsNone(self._store.get_tokens("google"))
        self._table.get_item.assert_called_once_with(Key={"provider": "google"})

    def test_get_tokens_returns_dict_when_item_exists(self) -> None:
        tokens = {"access_token": "ddb-tok", "expires_in": 3600}
        self._table.get_item.return_value = {"Item": {"provider": "google", "tokens": json.dumps(tokens)}}
        result = self._store.get_tokens("google")
        self.assertEqual(result, tokens)

    # ------------------------------------------------------------------ set_tokens

    def test_set_tokens_calls_put_item_with_json_serialised_tokens(self) -> None:
        tokens = {"access_token": "new-tok"}
        self._store.set_tokens("microsoft", tokens)
        self._table.put_item.assert_called_once_with(
            Item={"provider": "microsoft", "tokens": json.dumps(tokens)}
        )

    # ------------------------------------------------------------------ clear_tokens

    def test_clear_tokens_calls_delete_item(self) -> None:
        self._store.clear_tokens("google")
        self._table.delete_item.assert_called_once_with(Key={"provider": "google"})

    # ------------------------------------------------------------------ merge_tokens

    def test_merge_tokens_merges_into_existing_tokens(self) -> None:
        existing = {"access_token": "old-tok", "scope": "email"}
        self._table.get_item.return_value = {"Item": {"provider": "google", "tokens": json.dumps(existing)}}
        self._store.merge_tokens("google", {"access_token": "new-tok"})
        expected = {"access_token": "new-tok", "scope": "email"}
        self._table.put_item.assert_called_once_with(
            Item={"provider": "google", "tokens": json.dumps(expected)}
        )

    def test_merge_tokens_creates_provider_if_absent(self) -> None:
        self._table.get_item.return_value = {}
        self._store.merge_tokens("microsoft", {"access_token": "ms-tok"})
        self._table.put_item.assert_called_once_with(
            Item={"provider": "microsoft", "tokens": json.dumps({"access_token": "ms-tok"})}
        )

    # ------------------------------------------------------------------ plaid_status

    def test_plaid_status_no_token(self) -> None:
        self._table.get_item.return_value = {}
        status = self._store.plaid_status()
        self.assertFalse(status["has_access_token"])
        self.assertIsNone(status["institution_id"])

    def test_plaid_status_with_token(self) -> None:
        plaid_tokens = {"access_token": "plaid-tok", "institution_id": "ins_123"}
        self._table.get_item.return_value = {"Item": {"provider": "plaid", "tokens": json.dumps(plaid_tokens)}}
        status = self._store.plaid_status()
        self.assertTrue(status["has_access_token"])
        self.assertEqual(status["institution_id"], "ins_123")

    # ------------------------------------------------------------------ expires_at

    def test_expires_at_returns_none_when_no_tokens(self) -> None:
        self._table.get_item.return_value = {}
        self.assertIsNone(self._store.expires_at("google"))

    def test_expires_at_returns_value_when_set(self) -> None:
        tokens = {"access_token": "tok", "expires_at": "2026-01-01T00:00:00+00:00"}
        self._table.get_item.return_value = {"Item": {"provider": "google", "tokens": json.dumps(tokens)}}
        self.assertEqual(self._store.expires_at("google"), "2026-01-01T00:00:00+00:00")

    # ------------------------------------------------------------------ dispatch check

    def test_file_based_store_has_no_table(self) -> None:
        """When OAUTH_TOKEN_TABLE is absent, _table must be None."""
        os.environ.pop("OAUTH_TOKEN_TABLE", None)
        store = DevTokenStore("/tmp/some_path.json")
        self.assertIsNone(store._table)
