from __future__ import annotations

from assistant_app.models import CalendarEvent


class GoogleCalendarAdapter:
    key = "google_calendar"
    display_name = "Google Calendar"
    capabilities = ["calendar.read", "calendar.write", "reminders"]

    def list_mock_events(self) -> list[CalendarEvent]:
        return [
            CalendarEvent(
                id="gcal-1",
                title="Team sync",
                start="2026-03-17T09:00:00-04:00",
                end="2026-03-17T10:00:00-04:00",
                source=self.key,
                reminder_minutes=30,
            ),
            CalendarEvent(
                id="gcal-2",
                title="Client call",
                start="2026-03-17T11:30:00-04:00",
                end="2026-03-17T12:30:00-04:00",
                source=self.key,
                reminder_minutes=15,
            ),
        ]

    def normalize_event(self, payload: dict) -> CalendarEvent:
        reminder_minutes = None
        reminders = payload.get("reminders") or {}
        for reminder in reminders.get("overrides", []):
            reminder_minutes = reminder.get("minutes")
            break

        start = payload.get("start", {})
        end = payload.get("end", {})
        return CalendarEvent(
            id=payload["id"],
            title=payload.get("summary", "Untitled event"),
            start=start.get("dateTime") or start.get("date", ""),
            end=end.get("dateTime") or end.get("date", ""),
            source=self.key,
            location=payload.get("location", ""),
            notes=payload.get("description", ""),
            reminder_minutes=reminder_minutes,
        )
