"""Tests for config.py startup validation — live Lambda credential checks."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from assistant_app.config import AppConfig, _validate_live_credentials


_ALL_CREDENTIALS = {
    "GOOGLE_CLIENT_ID": "gid",
    "GOOGLE_CLIENT_SECRET": "gsecret",
    "MICROSOFT_CLIENT_ID": "msid",
    "MICROSOFT_CLIENT_SECRET": "mssecret",
    "PLAID_CLIENT_ID": "plaidid",
    "PLAID_SECRET": "plaidsecret",
}


class ValidateLiveCredentialsTests(unittest.TestCase):
    """Unit tests for _validate_live_credentials()."""

    def test_validate_live_credentials_raises_when_all_missing(self) -> None:
        """With no credentials in env, RuntimeError must mention all 6 missing keys."""
        keys = [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "MICROSOFT_CLIENT_ID",
            "MICROSOFT_CLIENT_SECRET",
            "PLAID_CLIENT_ID",
            "PLAID_SECRET",
        ]
        # Ensure none of the credential vars are set
        with patch.dict("os.environ", {k: "" for k in keys}, clear=False):
            with self.assertRaises(RuntimeError) as ctx:
                _validate_live_credentials()
        error_message = str(ctx.exception)
        for key in keys:
            self.assertIn(key, error_message)

    def test_validate_live_credentials_raises_when_partial_missing(self) -> None:
        """When only some credentials are set, error must mention only the missing ones."""
        present = {
            "GOOGLE_CLIENT_ID": "gid",
            "GOOGLE_CLIENT_SECRET": "gsecret",
        }
        absent = {
            "MICROSOFT_CLIENT_ID": "",
            "MICROSOFT_CLIENT_SECRET": "",
            "PLAID_CLIENT_ID": "",
            "PLAID_SECRET": "",
        }
        with patch.dict("os.environ", {**present, **absent}, clear=False):
            with self.assertRaises(RuntimeError) as ctx:
                _validate_live_credentials()
        error_message = str(ctx.exception)
        # Missing keys should appear
        self.assertIn("MICROSOFT_CLIENT_ID", error_message)
        self.assertIn("MICROSOFT_CLIENT_SECRET", error_message)
        self.assertIn("PLAID_CLIENT_ID", error_message)
        self.assertIn("PLAID_SECRET", error_message)
        # Present keys must NOT appear as missing
        self.assertNotIn("GOOGLE_CLIENT_ID", error_message)
        self.assertNotIn("GOOGLE_CLIENT_SECRET", error_message)

    def test_validate_live_credentials_passes_when_all_present(self) -> None:
        """When all 6 credentials are set, no exception is raised."""
        with patch.dict("os.environ", _ALL_CREDENTIALS, clear=False):
            # Must not raise
            _validate_live_credentials()


class FromEnvLiveValidationTests(unittest.TestCase):
    """Integration tests for AppConfig.from_env() validation gate."""

    def test_from_env_raises_in_lambda_live_mode_when_secrets_missing(self) -> None:
        """When load_secrets_from_manager returns {} and Lambda+live mode is set, from_env() raises."""
        credential_vars = [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "MICROSOFT_CLIENT_ID",
            "MICROSOFT_CLIENT_SECRET",
            "PLAID_CLIENT_ID",
            "PLAID_SECRET",
        ]
        env_overrides = {
            "AWS_LAMBDA_FUNCTION_NAME": "my-lambda",
            "MOCK_PROVIDER_MODE": "false",
            **{k: "" for k in credential_vars},
        }
        with patch(
            "assistant_app.secrets_manager.load_secrets_from_manager",
            return_value={},
        ):
            with patch.dict("os.environ", env_overrides, clear=False):
                with self.assertRaises(RuntimeError) as ctx:
                    AppConfig.from_env()
        self.assertIn("live mode", str(ctx.exception))

    def test_from_env_does_not_raise_in_mock_mode(self) -> None:
        """When MOCK_PROVIDER_MODE=true, from_env() must not raise even with no credentials."""
        credential_vars = [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "MICROSOFT_CLIENT_ID",
            "MICROSOFT_CLIENT_SECRET",
            "PLAID_CLIENT_ID",
            "PLAID_SECRET",
        ]
        env_overrides = {
            "AWS_LAMBDA_FUNCTION_NAME": "my-lambda",
            "MOCK_PROVIDER_MODE": "true",
            **{k: "" for k in credential_vars},
        }
        with patch(
            "assistant_app.secrets_manager.load_secrets_from_manager",
            return_value={},
        ):
            with patch.dict("os.environ", env_overrides, clear=False):
                # Must not raise
                config = AppConfig.from_env()
        self.assertTrue(config.mock_provider_mode)
