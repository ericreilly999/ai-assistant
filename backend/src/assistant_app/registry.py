from __future__ import annotations

from assistant_app.providers.google_calendar import GoogleCalendarAdapter
from assistant_app.providers.google_drive import GoogleDriveAdapter
from assistant_app.providers.google_tasks import GoogleTasksAdapter
from assistant_app.providers.microsoft_calendar import MicrosoftCalendarAdapter
from assistant_app.providers.microsoft_todo import MicrosoftToDoAdapter
from assistant_app.providers.plaid import PlaidAdapter


class ProviderRegistry:
    def __init__(self, mock_mode: bool = True) -> None:
        self.mock_mode = mock_mode
        self._adapters = {
            GoogleCalendarAdapter.key: GoogleCalendarAdapter(),
            GoogleTasksAdapter.key: GoogleTasksAdapter(),
            GoogleDriveAdapter.key: GoogleDriveAdapter(),
            MicrosoftCalendarAdapter.key: MicrosoftCalendarAdapter(),
            MicrosoftToDoAdapter.key: MicrosoftToDoAdapter(),
            PlaidAdapter.key: PlaidAdapter(),
        }

    def get(self, provider_name: str):
        return self._adapters[provider_name]

    def providers(self) -> list[str]:
        return list(self._adapters.keys())

    def integration_status(self) -> list[dict[str, object]]:
        return [
            {
                "provider": name,
                "display_name": adapter.display_name,
                "capabilities": list(adapter.capabilities),
                "mock_mode": self.mock_mode,
            }
            for name, adapter in self._adapters.items()
        ]