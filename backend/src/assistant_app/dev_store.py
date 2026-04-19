from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class DevTokenStore:
    """Token store used during development OAuth flows.

    Dispatch is determined at construction time by the ``OAUTH_TOKEN_TABLE``
    environment variable:

    * If set → DynamoDB-backed (shared across Lambda container instances).
    * If not set → File-backed (local development without AWS credentials).
    """

    def __init__(self, store_file: str) -> None:
        self._path = Path(store_file)

        table_name = os.environ.get("OAUTH_TOKEN_TABLE")
        if table_name:
            import boto3
            self._table = boto3.resource("dynamodb").Table(table_name)
        else:
            self._table = None

    # ------------------------------------------------------------------
    # File-backed helpers (used only when OAUTH_TOKEN_TABLE is not set)
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            text = self._path.read_text(encoding="utf-8").strip()
            if not text:
                return {}
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public interface — works in both file and DynamoDB modes
    # ------------------------------------------------------------------

    def _ddb_key(self, user_id: str, provider: str) -> str:
        """Return the DynamoDB partition key value scoped to a specific user.

        Format: ``{user_id}#{provider}``

        Using a composite value rather than a separate sort key keeps the table
        schema (single string hash_key ``provider``) unchanged while ensuring
        that one user's OAuth tokens can never overwrite another user's record.
        """
        return f"{user_id}#{provider}"

    def get_tokens(self, provider: str, user_id: str = "local") -> dict[str, Any] | None:
        if self._table is not None:
            key = self._ddb_key(user_id, provider)
            response = self._table.get_item(Key={"provider": key})
            item = response.get("Item")
            if item is None:
                return None
            return json.loads(item["tokens"])
        return self.load().get(provider)

    def set_tokens(self, provider: str, tokens: dict[str, Any], user_id: str = "local") -> None:
        if self._table is not None:
            key = self._ddb_key(user_id, provider)
            self._table.put_item(Item={"provider": key, "tokens": json.dumps(tokens)})
            return
        data = self.load()
        data[provider] = tokens
        self.save(data)

    def clear_tokens(self, provider: str, user_id: str = "local") -> None:
        if self._table is not None:
            key = self._ddb_key(user_id, provider)
            self._table.delete_item(Key={"provider": key})
            return
        data = self.load()
        data.pop(provider, None)
        self.save(data)

    def merge_tokens(self, provider: str, updates: dict[str, Any], user_id: str = "local") -> None:
        existing = self.get_tokens(provider, user_id=user_id) or {}
        existing.update(updates)
        self.set_tokens(provider, existing, user_id=user_id)

    def plaid_status(self, user_id: str = "local") -> dict[str, Any]:
        plaid = self.get_tokens("plaid", user_id=user_id) or {}
        return {
            "has_access_token": bool(plaid.get("access_token")),
            "institution_id": plaid.get("institution_id"),
        }

    def expires_at(self, provider: str, user_id: str = "local") -> str | None:
        tokens = self.get_tokens(provider, user_id=user_id)
        if tokens is None:
            return None
        return tokens.get("expires_at")
