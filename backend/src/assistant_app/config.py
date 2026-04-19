from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _load_local_env(env_file: str) -> None:
    """Parse a .env-style file and populate os.environ for any keys not already set."""
    path = Path(env_file)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _default_store_file() -> str:
    """Return the default token store path.

    In Lambda (detected by AWS_LAMBDA_FUNCTION_NAME being set) the only
    writable location is /tmp, so we use /tmp/dev_tokens.json.  For local
    development we keep the project-relative path so nothing changes.
    """
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/dev_tokens.json"
    return "backend/.local/dev_tokens.json"


def _validate_live_credentials() -> None:
    """Raise RuntimeError if any required provider credential is missing in live Lambda mode."""
    required = {
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "MICROSOFT_CLIENT_ID": os.getenv("MICROSOFT_CLIENT_ID"),
        "MICROSOFT_CLIENT_SECRET": os.getenv("MICROSOFT_CLIENT_SECRET"),
        "PLAID_CLIENT_ID": os.getenv("PLAID_CLIENT_ID"),
        "PLAID_SECRET": os.getenv("PLAID_SECRET"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(
            f"Lambda started in live mode but required credentials are missing: {missing}. "
            "Check Secrets Manager ARN env vars and IAM permissions."
        )


def _compute_provider_secret_status() -> dict[str, bool]:
    return {
        "google": bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")),
        "microsoft": bool(os.getenv("MICROSOFT_CLIENT_ID") and os.getenv("MICROSOFT_CLIENT_SECRET")),
        "plaid": bool(os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET")),
    }


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    log_level: str
    mock_provider_mode: bool
    proposal_ttl_minutes: int
    default_timezone: str
    bedrock_router_model_id: str
    bedrock_guardrail_id: str
    bedrock_guardrail_version: str

    # Local dev paths
    local_env_file: str | None = None
    local_store_file: str = "backend/.local/dev_tokens.json"

    # OAuth credentials (loaded from env or .env.local)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8787/oauth/google/callback"
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8787/oauth/microsoft/callback"
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"

    # Agent loop configuration
    max_agent_turns: int = 5

    # Computed: which providers have secrets available
    provider_secret_status: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> AppConfig:
        # Load secrets from AWS Secrets Manager at cold start (if in Lambda)
        from assistant_app.secrets_manager import load_secrets_from_manager
        load_secrets_from_manager()

        # Validate required credentials are present when running live in Lambda
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME") and not _bool_env("MOCK_PROVIDER_MODE", True):
            _validate_live_credentials()

        local_env_file = os.getenv("LOCAL_ENV_FILE", "backend/.env.local")
        if os.path.exists(local_env_file):
            _load_local_env(local_env_file)
            resolved_env_file: str | None = local_env_file
        else:
            resolved_env_file = None

        local_server_port = os.getenv("LOCAL_SERVER_PORT", "8787")

        return cls(
            app_env=os.getenv("APP_ENV", "dev"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            mock_provider_mode=_bool_env("MOCK_PROVIDER_MODE", True),
            proposal_ttl_minutes=int(os.getenv("PROPOSAL_TTL_MINUTES", "15")),
            default_timezone=os.getenv("DEFAULT_TIMEZONE", "America/New_York"),
            bedrock_router_model_id=os.getenv("BEDROCK_ROUTER_MODEL_ID", "mock-router"),
            bedrock_guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID", "mock-guardrail"),
            bedrock_guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
            local_env_file=resolved_env_file,
            local_store_file=os.getenv("LOCAL_STORE_FILE", _default_store_file()),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            google_redirect_uri=os.getenv(
                "GOOGLE_REDIRECT_URI",
                f"http://localhost:{local_server_port}/oauth/google/callback",
            ),
            microsoft_client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
            microsoft_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
            microsoft_redirect_uri=os.getenv(
                "MICROSOFT_REDIRECT_URI",
                f"http://localhost:{local_server_port}/oauth/microsoft/callback",
            ),
            plaid_client_id=os.getenv("PLAID_CLIENT_ID", ""),
            plaid_secret=os.getenv("PLAID_SECRET", ""),
            plaid_env=os.getenv("PLAID_ENV", "sandbox"),
            max_agent_turns=int(os.getenv("MAX_AGENT_TURNS", "5")),
            provider_secret_status=_compute_provider_secret_status(),
        )
