from __future__ import annotations

from assistant_app.models import CalendarEvent


class MicrosoftCalendarAdapter:
    key = "microsoft_calendar"
    display_name = "Microsoft 365 Calendar"
    capabilities = ["calendar.read", "calendar.write", "reminders"]

    def list_mock_events(self) -> list[CalendarEvent]:
        return [
            CalendarEvent(
                id="mscal-1",
                title="Architecture review",
                start="2026-03-17T15:00:00-04:00",
                end="2026-03-17T16:00:00-04:00",
                source=self.key,
                reminder_minutes=10,
            )
        ]

    def normalize_event(self, payload: dict) -> CalendarEvent:
        start = payload.get("start", {})
        end = payload.get("end", {})
        return CalendarEvent(
            id=payload["id"],
            title=payload.get("subject", "Untitled event"),
            start=start.get("dateTime", ""),
            end=end.get("dateTime", ""),
            source=self.key,
            location=(payload.get("location") or {}).get("displayName", ""),
            notes=(payload.get("bodyPreview") or ""),
            reminder_minutes=payload.get("reminderMinutesBeforeStart"),
        )