from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from assistant_app.dev_store import DevTokenStore


class DevTokenStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store_path = os.path.join(self._tmpdir, "tokens.json")
        self.store = DevTokenStore(self._store_path)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

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
