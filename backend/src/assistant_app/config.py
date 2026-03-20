from __future__ import annotations

from dataclasses import dataclass
import os


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


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

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            app_env=os.getenv("APP_ENV", "dev"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            mock_provider_mode=_bool_env("MOCK_PROVIDER_MODE", True),
            proposal_ttl_minutes=int(os.getenv("PROPOSAL_TTL_MINUTES", "15")),
            default_timezone=os.getenv("DEFAULT_TIMEZONE", "America/New_York"),
            bedrock_router_model_id=os.getenv("BEDROCK_ROUTER_MODEL_ID", "mock-router"),
            bedrock_guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID", "mock-guardrail"),
            bedrock_guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        )