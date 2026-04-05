from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DevTokenStore:
    """File-backed token store used only during local development OAuth flows."""

    def __init__(self, store_file: str) -> None:
        self._path = Path(store_file)

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

    def get_tokens(self, provider: str) -> dict[str, Any] | None:
        return self.load().get(provider)

    def set_tokens(self, provider: str, tokens: dict[str, Any]) -> None:
        data = self.load()
        data[provider] = tokens
        self.save(data)

    def clear_tokens(self, provider: str) -> None:
        data = self.load()
        data.pop(provider, None)
        self.save(data)

    def merge_tokens(self, provider: str, updates: dict[str, Any]) -> None:
        data = self.load()
        existing = data.get(provider) or {}
        existing.update(updates)
        data[provider] = existing
        self.save(data)

    def plaid_status(self) -> dict[str, Any]:
        data = self.load()
        plaid = data.get("plaid") or {}
        return {
            "has_access_token": bool(plaid.get("access_token")),
            "institution_id": plaid.get("institution_id"),
        }

    def expires_at(self, provider: str) -> str | None:
        tokens = self.get_tokens(provider)
        if tokens is None:
            return None
        return tokens.get("expires_at")
