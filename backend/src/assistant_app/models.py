from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    start: str
    end: str
    source: str
    location: str = ""
    notes: str = ""
    reminder_minutes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskItem:
    id: str
    title: str
    source: str
    status: str
    list_name: str
    due: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentReference:
    id: str
    title: str
    source: str
    mime_type: str
    web_view_link: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinancialAccount:
    id: str
    name: str
    source: str
    mask: str
    subtype: str
    available_balance: float | None
    current_balance: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    provider: str
    action_type: str
    resource_type: str
    payload: dict[str, Any]
    payload_hash: str
    summary: str
    risk_level: str
    requires_confirmation: bool
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanResult:
    intent: str
    message: str
    proposals: list[ActionProposal] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "message": self.message,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
            "sources": list(self.sources),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ExecuteResult:
    message: str
    provider: str
    action_type: str
    receipt: dict[str, Any]
    resource: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
