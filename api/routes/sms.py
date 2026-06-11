"""
Email Sail Agent — SMS API Routes
"""

import logging

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user
from api.services.twilio_service import TwilioService
from api.database import get_db

logger = logging.getLogger("email-sail.sms")
router = APIRouter()


@router.post("/send")
async def send_sms(request: Request):
    """Send an SMS to a customer."""
    user = require_user(request)
    body = await request.json()

    to_number = body.get("to")
    sms_body = body.get("body", "")
    thread_id = body.get("thread_id")

    if not to_number or not sms_body:
        raise HTTPException(status_code=400, detail="Missing to or body")

    # Get user's Twilio settings from DB
    db = await get_db()
    cursor = await db.execute(
        "SELECT twilio_sid, twilio_auth_token, twilio_phone FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    settings_row = await cursor.fetchone()
    await db.close()

    twilio = TwilioService(
        account_sid=settings_row["twilio_sid"] if settings_row else None,
        auth_token=settings_row["twilio_auth_token"] if settings_row else None,
        from_number=settings_row["twilio_phone"] if settings_row else None,
    )

    try:
        result = await twilio.send_sms(to_number, sms_body)

        # Log to DB
        db = await get_db()
        await db.execute(
            """INSERT INTO sms_log
               (user_id, thread_id, to_number, from_number, body, twilio_sid, direction, status, sent_at)
               VALUES (?, ?, ?, ?, ?, ?, 'outbound', ?, datetime('now'))""",
            (user["google_id"], thread_id, to_number,
             twilio.from_number, sms_body, result["sid"], result["status"]),
        )
        await db.commit()
        await db.close()

        return {"sent": True, "sid": result["sid"], "status": result["status"]}
    except Exception as e:
        logger.error("Error sending SMS: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft")
async def draft_sms(request: Request):
    """Draft an SMS (doesn't send, just returns the text)."""
    user = require_user(request)
    body = await request.json()

    customer_name = body.get("customer_name", "there")
    message_type = body.get("message_type", "follow_up")

    twilio = TwilioService()
    draft = twilio.format_sms_draft(customer_name, message_type)

    return {"draft": draft, "length": len(draft)}
