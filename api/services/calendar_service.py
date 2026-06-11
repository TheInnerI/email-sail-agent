"""
Email Sail Agent — Google Calendar Service
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger("email-sail.calendar")

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


class CalendarService:
    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def list_calendars(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{CALENDAR_API_BASE}/users/me/calendarList",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("items", [])

    async def get_events(
        self,
        calendar_id: str = "primary",
        time_min: str = None,
        time_max: str = None,
        max_results: int = 50,
    ) -> list[dict]:
        params = {"maxResults": max_results, "singleEvents": "true", "orderBy": "startTime"}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("items", [])

    async def find_free_slots(
        self,
        duration_minutes: int = 30,
        days_ahead: int = 7,
        business_hours: tuple = (9, 17),
        calendar_id: str = "primary",
    ) -> list[dict]:
        """
        Find available time slots in the next N days.
        Returns list of {"start": ISO, "end": ISO, "display": str}
        """
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

        events = await self.get_events(calendar_id, time_min, time_max)

        # Build busy periods
        busy = []
        for event in events:
            start = event.get("start", {}).get("dateTime")
            end = event.get("end", {}).get("dateTime")
            if start and end:
                busy.append((datetime.fromisoformat(start.replace("Z", "+00:00")),
                             datetime.fromisoformat(end.replace("Z", "+00:00"))))

        busy.sort(key=lambda x: x[0])

        # Find free slots during business hours
        free_slots = []
        current = now.replace(minute=0, second=0, microsecond=0)
        if current.hour < business_hours[0]:
            current = current.replace(hour=business_hours[0])

        for day_offset in range(days_ahead):
            day = current + timedelta(days=day_offset)
            if day.weekday() >= 5:  # Skip weekends
                continue

            for hour in range(business_hours[0], business_hours[1]):
                slot_start = day.replace(hour=hour, minute=0)
                slot_end = slot_start + timedelta(minutes=duration_minutes)

                # Check if slot overlaps with any busy period
                is_free = True
                for busy_start, busy_end in busy:
                    if slot_start < busy_end and slot_end > busy_start:
                        is_free = False
                        break

                if is_free and slot_start > now:
                    free_slots.append({
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                        "display": slot_start.strftime("%A, %B %d at %I:%M %p"),
                    })

                if len(free_slots) >= 10:
                    break

            if len(free_slots) >= 10:
                break

        return free_slots

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: list[str] = None,
        calendar_id: str = "primary",
    ) -> dict:
        """Create a calendar event."""
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                headers=self.headers,
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers=self.headers,
                timeout=30,
            )
