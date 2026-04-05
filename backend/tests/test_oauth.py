from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from assistant_app.config import AppConfig
from assistant_app.live_service import LocalIntegrationService
from assistant_app.registry import ProviderRegistry


def _make_config(**overrides):
    defaults = {
        "app_env": "dev",
        "log_level": "INFO",
        "mock_provider_mode": True,
        "proposal_ttl_minutes": 15,
        "default_timezone": "America/New_York",
        "bedrock_router_model_id": "mock-router",
        "bedrock_guardrail_id": "mock-guardrail",
        "bedrock_guardrail_version": "DRAFT",
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


class GoogleOAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store_path = os.path.join(self._tmpdir, "tokens.json")
        self.config = _make_config(
            google_client_id="g-client-id",
            google_client_secret="g-client-secret",
            google_redirect_uri="http://localhost:8787/oauth/google/callback",
            local_store_file=self._store_path,
        )
        self.service = LocalIntegrationService(self.config, ProviderRegistry(mock_mode=True))

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_google_auth_url_raises_when_not_configured(self) -> None:
        service = LocalIntegrationService(
            _make_config(local_store_file=self._store_path),
            ProviderRegistry(mock_mode=True),
        )
        with self.assertRaises(ValueError) as ctx:
            service.google_auth_url()
        self.assertIn("GOOGLE_CLIENT_ID", str(ctx.exception))

    def test_google_auth_url_contains_client_id(self) -> None:
        url = self.service.google_auth_url()
        self.assertIn("g-client-id", url)
        self.assertIn("accounts.google.com", url)

    def test_google_auth_url_contains_required_params(self) -> None:
        url = self.service.google_auth_url()
        self.assertIn("redirect_uri", url)
        self.assertIn("response_type=code", url)
        self.assertIn("scope", url)

    def test_complete_google_auth_raises_when_not_configured(self) -> None:
        service = LocalIntegrationService(
            _make_config(local_store_file=self._store_path),
            ProviderRegistry(mock_mode=True),
        )
        with self.assertRaises(ValueError):
            service.complete_google_auth("code-123", "state-abc")

    def test_complete_google_auth_stores_tokens(self) -> None:
        mock_tokens = {
            "access_token": "g-access",
            "refresh_token": "g-refresh",
            "scope": "email openid",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        with patch("assistant_app.live_service.http_post_form", return_value=mock_tokens):
            result = self.service.complete_google_auth("auth-code", "state-abc")
        self.assertTrue(result["stored"])
        tokens = self.service._store.get_tokens("google")
        self.assertEqual(tokens["access_token"], "g-access")  # type: ignore[index]

    def test_google_token_raises_when_not_connected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.service._google_token()
        self.assertIn("not connected", str(ctx.exception))


class MicrosoftOAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store_path = os.path.join(self._tmpdir, "tokens.json")
        self.config = _make_config(
            microsoft_client_id="ms-client-id",
            microsoft_client_secret="ms-client-secret",
            microsoft_redirect_uri="http://localhost:8787/oauth/microsoft/callback",
            local_store_file=self._store_path,
        )
        self.service = LocalIntegrationService(self.config, ProviderRegistry(mock_mode=True))

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_microsoft_auth_url_raises_when_not_configured(self) -> None:
        service = LocalIntegrationService(
            _make_config(local_store_file=self._store_path),
            ProviderRegistry(mock_mode=True),
        )
        with self.assertRaises(ValueError) as ctx:
            service.microsoft_auth_url()
        self.assertIn("MICROSOFT_CLIENT_ID", str(ctx.exception))

    def test_microsoft_auth_url_contains_client_id(self) -> None:
        url = self.service.microsoft_auth_url()
        self.assertIn("ms-client-id", url)
        self.assertIn("microsoftonline.com", url)

    def test_microsoft_auth_url_contains_required_params(self) -> None:
        url = self.service.microsoft_auth_url()
        self.assertIn("redirect_uri", url)
        self.assertIn("response_type=code", url)

    def test_complete_microsoft_auth_stores_tokens(self) -> None:
        mock_tokens = {
            "access_token": "ms-access",
            "refresh_token": "ms-refresh",
            "scope": "Calendars.ReadWrite",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        with patch("assistant_app.live_service.http_post_form", return_value=mock_tokens):
            result = self.service.complete_microsoft_auth("auth-code", "state-abc")
        self.assertTrue(result["stored"])
        tokens = self.service._store.get_tokens("microsoft")
        self.assertEqual(tokens["access_token"], "ms-access")  # type: ignore[index]

    def test_ms_token_raises_when_not_connected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.service._ms_token()
        self.assertIn("not connected", str(ctx.exception))

    def test_state_mismatch_does_not_store_on_failure(self) -> None:
        with patch(
            "assistant_app.live_service.http_post_form",
            side_effect=ValueError("exchange failed"),
        ), self.assertRaises(ValueError):
            self.service.complete_microsoft_auth("bad-code", "state-xyz")
        self.assertIsNone(self.service._store.get_tokens("microsoft"))


class RequiredConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store_path = os.path.join(self._tmpdir, "tokens.json")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_plaid_bootstrap_raises_when_not_configured(self) -> None:
        service = LocalIntegrationService(
            _make_config(local_store_file=self._store_path),
            ProviderRegistry(mock_mode=True),
        )
        with self.assertRaises(ValueError) as ctx:
            service.bootstrap_plaid_sandbox("ins_12345")
        self.assertIn("PLAID_CLIENT_ID", str(ctx.exception))

    def test_connection_status_all_disconnected_initially(self) -> None:
        service = LocalIntegrationService(
            _make_config(local_store_file=self._store_path),
            ProviderRegistry(mock_mode=True),
        )
        status = service.connection_status()
        self.assertFalse(status["google"]["connected"])
        self.assertFalse(status["microsoft"]["connected"])
        self.assertFalse(status["plaid"]["has_access_token"])
