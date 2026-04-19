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

    def get_tokens(self, provider: str) -> dict[str, Any] | None:
        if self._table is not None:
            response = self._table.get_item(Key={"provider": provider})
            item = response.get("Item")
            if item is None:
                return None
            return json.loads(item["tokens"])
        return self.load().get(provider)

    def set_tokens(self, provider: str, tokens: dict[str, Any]) -> None:
        if self._table is not None:
            self._table.put_item(Item={"provider": provider, "tokens": json.dumps(tokens)})
            return
        data = self.load()
        data[provider] = tokens
        self.save(data)

    def clear_tokens(self, provider: str) -> None:
        if self._table is not None:
            self._table.delete_item(Key={"provider": provider})
            return
        data = self.load()
        data.pop(provider, None)
        self.save(data)

    def merge_tokens(self, provider: str, updates: dict[str, Any]) -> None:
        existing = self.get_tokens(provider) or {}
        existing.update(updates)
        self.set_tokens(provider, existing)

    def plaid_status(self) -> dict[str, Any]:
        plaid = self.get_tokens("plaid") or {}
        return {
            "has_access_token": bool(plaid.get("access_token")),
            "institution_id": plaid.get("institution_id"),
        }

    def expires_at(self, provider: str) -> str | None:
        tokens = self.get_tokens(provider)
        if tokens is None:
            return None
        return tokens.get("expires_at")
