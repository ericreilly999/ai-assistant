"""AWS Secrets Manager integration for loading secrets at Lambda cold start."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def load_secrets_from_manager() -> dict[str, str]:
    """
    Load secrets from AWS Secrets Manager using ARNs from environment variables.

    Expected environment variables (set by Terraform):
    - GOOGLE_OAUTH_SECRET_ARN: ARN of secret containing google_client_id, google_client_secret
    - MICROSOFT_OAUTH_SECRET_ARN: ARN of secret containing microsoft_client_id, microsoft_client_secret
    - PLAID_SECRET_ARN: ARN of secret containing plaid_client_id, plaid_secret

    Returns:
        Dictionary of loaded secrets as environment variable names -> values.
        Returns empty dict if not in AWS Lambda or if secrets fail to load.
    """
    # Only load from Secrets Manager if in Lambda (has AWS_LAMBDA_FUNCTION_NAME)
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return {}

    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not available; skipping Secrets Manager loading")
        return {}

    client = boto3.client("secretsmanager")
    loaded_secrets: dict[str, str] = {}

    # Map of environment variable ARN -> list of environment variable names to set
    secret_arns = {
        "GOOGLE_OAUTH_SECRET_ARN": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "MICROSOFT_OAUTH_SECRET_ARN": ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET"],
        "PLAID_SECRET_ARN": ["PLAID_CLIENT_ID", "PLAID_SECRET"],
    }

    for env_var_name, expected_keys in secret_arns.items():
        secret_arn = os.getenv(env_var_name)
        if not secret_arn:
            logger.debug(f"Skipping {env_var_name}: not set")
            continue

        try:
            response = client.get_secret_value(SecretId=secret_arn)
            secret_value = response.get("SecretString") or response.get("SecretBinary")

            if not secret_value:
                logger.warning(f"Empty secret retrieved from {secret_arn}")
                continue

            # Parse JSON secret
            try:
                secret_dict = json.loads(secret_value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse secret {secret_arn} as JSON")
                continue

            # Extract expected keys and set environment variables
            for key in expected_keys:
                # Convert snake_case to kebab-case for secret key lookup
                # e.g., GOOGLE_CLIENT_ID -> google_client_id -> google-client-id
                secret_key = key.lower().replace("_", "-")

                if secret_key in secret_dict:
                    loaded_secrets[key] = secret_dict[secret_key]
                    # Set in os.environ if not already set
                    if key not in os.environ:
                        os.environ[key] = secret_dict[secret_key]
                else:
                    logger.warning(f"Key {secret_key} not found in secret {secret_arn}")

        except Exception as exc:
            logger.error(f"Failed to load secret from {secret_arn}: {exc}")

    return loaded_secrets
