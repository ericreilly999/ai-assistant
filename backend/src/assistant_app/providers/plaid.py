from __future__ import annotations

from assistant_app.models import FinancialAccount


class PlaidAdapter:
    key = "plaid"
    display_name = "Plaid"
    capabilities = ["finance.read"]

    def list_mock_accounts(self) -> list[FinancialAccount]:
        return [
            FinancialAccount(
                id="plaid-1",
                name="Everyday Checking",
                source=self.key,
                mask="1234",
                subtype="checking",
                available_balance=1580.25,
                current_balance=1600.25,
            )
        ]

    def normalize_account(self, payload: dict) -> FinancialAccount:
        balances = payload.get("balances") or {}
        return FinancialAccount(
            id=payload["account_id"],
            name=payload.get("name", "Unnamed account"),
            source=self.key,
            mask=payload.get("mask", ""),
            subtype=payload.get("subtype", ""),
            available_balance=balances.get("available"),
            current_balance=balances.get("current"),
        )
