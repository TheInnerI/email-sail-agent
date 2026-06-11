"""
Email Sail Agent — Calendar API Routes
"""

import logging

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user
from api.services.calendar_service import CalendarService
from api.database import get_db

logger = logging.getLogger("email-sail.calendar")
router = APIRouter()


@router.get("/events")
async def get_events(request: Request, days: int = 7):
    """Get calendar events for the next N days."""
    user = require_user(request)
    cal = CalendarService(user["access_token"])

    try:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days)).isoformat() + "Z"
        events = await cal.get_events(time_min=time_min, time_max=time_max)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error("Error fetching events: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free-slots")
async def get_free_slots(
    request: Request,
    duration: int = 30,
    days: int = 7,
):
    """Find available time slots."""
    user = require_user(request)
    cal = CalendarService(user["access_token"])

    try:
        slots = await cal.find_free_slots(duration_minutes=duration, days_ahead=days)
        return {"slots": slots, "count": len(slots)}
    except Exception as e:
        logger.error("Error finding free slots: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/book")
async def book_appointment(request: Request):
    """Book an appointment."""
    user = require_user(request)
    body = await request.json()

    customer_name = body.get("customer_name", "Customer")
    customer_email = body.get("customer_email", "")
    start_time = body.get("start_time")
    end_time = body.get("end_time")
    notes = body.get("notes", "")

    if not start_time or not end_time:
        raise HTTPException(status_code=400, detail="Missing start_time or end_time")

    cal = CalendarService(user["access_token"])

    try:
        event = await cal.create_event(
            summary=f"Meeting with {customer_name}",
            start_time=start_time,
            end_time=end_time,
            description=notes,
            attendees=[customer_email] if customer_email else None,
        )

        # Log to DB
        db = await get_db()
        await db.execute(
            """INSERT INTO appointments
               (user_id, customer_name, customer_email, event_id, start_time, end_time, status, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'booked', ?, datetime('now'))""",
            (user["google_id"], customer_name, customer_email,
             event["id"], start_time, end_time, notes),
        )
        await db.commit()
        await db.close()

        return {
            "booked": True,
            "event_id": event["id"],
            "event_link": event.get("htmlLink", ""),
            "start": start_time,
            "end": end_time,
        }
    except Exception as e:
        logger.error("Error booking appointment: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
