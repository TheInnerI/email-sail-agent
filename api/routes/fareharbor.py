"""
Email Sail Agent — FareHarbor API Routes

FareHarbor booking management + webhook handler.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user
from api.services.fareharbor_service import FareHarborService
from api.database import get_db

logger = logging.getLogger("email-sail.fareharbor")
router = APIRouter(prefix="/api/fareharbor", tags=["fareharbor"])


def get_fh_service(user: dict) -> Optional[FareHarborService]:
    """Get FareHarbor service from user settings."""
    # In production, load from DB. For now, return None if not configured.
    return None  # Will be wired to user_settings table


@router.get("/items")
async def list_items(request: Request):
    """List all bookable items/tours."""
    user = require_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        return {"items": [], "configured": False, "message": "FareHarbor not configured. Add your API key in Settings."}

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        items = await fh.get_items()
        return {"items": items, "configured": True, "count": len(items)}
    except Exception as e:
        logger.error("FH items error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{item_id}/availabilities")
async def get_availabilities(request: Request, item_id: int, date: str = None):
    """Get available time slots for an item."""
    user = require_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        raise HTTPException(status_code=400, detail="FareHarbor not configured")

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        slots = await fh.get_availabilities(item_id, date=date)
        return {"availabilities": slots, "count": len(slots)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bookings")
async def list_bookings(
    request: Request,
    date: str = None,
    status: str = None,
):
    """List bookings."""
    user = require_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        return {"bookings": [], "configured": False}

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        bookings = await fh.get_bookings(date=date, status=status)
        parsed = [fh.parse_booking(b) for b in bookings]
        return {"bookings": parsed, "count": len(parsed)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bookings/today")
async def today_bookings(request: Request):
    """Get today's bookings."""
    user = require_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        return {"bookings": [], "configured": False}

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        bookings = await fh.get_today_bookings()
        parsed = [fh.parse_booking(b) for b in bookings]
        return {"bookings": parsed, "count": len(parsed)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bookings")
async def create_booking(request: Request):
    """Create a new booking."""
    user = require_user(request)
    body = await request.json()

    item_id = body.get("item_id")
    customers = body.get("customers", [])

    if not item_id or not customers:
        raise HTTPException(status_code=400, detail="Missing item_id or customers")

    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        raise HTTPException(status_code=400, detail="FareHarbor not configured")

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        booking = await fh.create_booking(item_id, customers, **body.get("extra", {}))
        return {"created": True, "booking": booking}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bookings/{booking_id}")
async def cancel_booking(request: Request, booking_id: int):
    """Cancel a booking."""
    user = require_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        raise HTTPException(status_code=400, detail="FareHarbor not configured")

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        result = await fh.cancel_booking(booking_id)
        return {"cancelled": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bookings/{booking_id}/note")
async def update_booking_note(request: Request, booking_id: int):
    """Update a booking note."""
    user = require_user(request)
    body = await request.json()
    note = body.get("note", "")

    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        raise HTTPException(status_code=400, detail="FareHarbor not configured")

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        result = await fh.update_booking_note(booking_id, note)
        return {"updated": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lookup")
async def lookup_by_email(request: Request, email: str, date: str = None):
    """Look up a booking by customer email."""
    user = require_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT fh_api_key, fh_company_shortname FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row or not row["fh_api_key"]:
        return {"booking": None, "configured": False}

    fh = FareHarborService(row["fh_api_key"], row["fh_company_shortname"])
    try:
        booking = await fh.find_booking_by_email(email, date=date)
        if booking:
            return {"booking": fh.parse_booking(booking), "found": True}
        return {"booking": None, "found": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Webhook Handler ──

webhook_router = APIRouter(prefix="/webhooks/fareharbor", tags=["fareharbor-webhooks"])


@webhook_router.post("/")
async def handle_fh_webhook(request: Request):
    """
    Handle FareHarbor webhooks.

    Supported events:
    - booking.created
    - booking.updated
    - booking.cancelled
    - booking.no_show
    - customer.created
    """
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    logger.info("FH webhook received: %s", event_type)

    try:
        if event_type == "booking.created":
            await _handle_booking_created(data)
        elif event_type == "booking.cancelled":
            await _handle_booking_cancelled(data)
        elif event_type == "booking.no_show":
            await _handle_no_show(data)
        elif event_type == "booking.updated":
            await _handle_booking_updated(data)
        elif event_type == "customer.created":
            await _handle_customer_created(data)
        else:
            logger.info("Unhandled FH webhook type: %s", event_type)
    except Exception as e:
        logger.error("FH webhook error: %s", e)

    return {"received": True}


async def _handle_booking_created(data: dict):
    """New booking → log in CRM, create welcome email draft."""
    customer = data.get("customer", {})
    item = data.get("item", {})
    logger.info("FH: New booking for %s — %s", customer.get("email"), item.get("name"))
    # TODO: Create draft welcome email, log to CRM


async def _handle_booking_cancelled(data: dict):
    """Cancellation → update CRM, draft rebooking offer."""
    customer = data.get("customer", {})
    logger.info("FH: Booking cancelled for %s", customer.get("email"))
    # TODO: Update CRM, draft rebooking offer


async def _handle_no_show(data: dict):
    """No-show → draft follow-up email."""
    customer = data.get("customer", {})
    item = data.get("item", {})
    logger.info("FH: No-show for %s — %s", customer.get("email"), item.get("name"))
    # TODO: Draft no-show follow-up with reschedule options


async def _handle_booking_updated(data: dict):
    """Booking changed → update CRM."""
    logger.info("FH: Booking updated")
    # TODO: Update CRM record


async def _handle_customer_created(data: dict):
    """New customer → add to CRM."""
    customer = data.get("customer", {})
    logger.info("FH: New customer %s", customer.get("email"))
    # TODO: Add to CRM
