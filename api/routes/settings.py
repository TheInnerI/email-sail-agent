"""
Email Sail Agent — Settings Routes
"""

import logging

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user
from api.database import get_db

logger = logging.getLogger("email-sail.settings")
router = APIRouter()


@router.get("/")
async def get_settings(request: Request):
    """Get user settings."""
    user = require_user(request)
    db = await get_db()

    cursor = await db.execute(
        "SELECT * FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    row = await cursor.fetchone()
    await db.close()

    if not row:
        return {
            "twilio_sid": "",
            "twilio_auth_token": "",
            "twilio_phone": "",
            "gumroad_key": "",
            "fh_api_key": "",
            "fh_company_shortname": "",
            "fh_auto_respond_faq": True,
            "fh_auto_request_reviews": True,
            "fh_review_delay_days": 1,
            "fh_no_show_followup": True,
            "tone_preference": "professional",
            "auto_classify": True,
            "auto_draft": True,
            "notify_sms": False,
            "notify_email": True,
            "church_discount": False,
        }

    return {
        "twilio_sid": row["twilio_sid"],
        "twilio_auth_token": "***" if row["twilio_auth_token"] else "",
        "twilio_phone": row["twilio_phone"],
        "gumroad_key": "***" if row["gumroad_key"] else "",
        "fh_api_key": "***" if row["fh_api_key"] else "",
        "fh_company_shortname": row["fh_company_shortname"],
        "fh_auto_respond_faq": bool(row["fh_auto_respond_faq"]),
        "fh_auto_request_reviews": bool(row["fh_auto_request_reviews"]),
        "fh_review_delay_days": row["fh_review_delay_days"],
        "fh_no_show_followup": bool(row["fh_no_show_followup"]),
        "tone_preference": row["tone_preference"],
        "auto_classify": bool(row["auto_classify"]),
        "auto_draft": bool(row["auto_draft"]),
        "notify_sms": bool(row["notify_sms"]),
        "notify_email": bool(row["notify_email"]),
        "church_discount": bool(row["church_discount"]),
    }


@router.post("/")
async def update_settings(request: Request):
    """Update user settings."""
    user = require_user(request)
    body = await request.json()

    db = await get_db()

    # Check if settings exist
    cursor = await db.execute(
        "SELECT id FROM user_settings WHERE user_id = ?",
        (user["google_id"],),
    )
    existing = await cursor.fetchone()

    if existing:
        await db.execute(
            """UPDATE user_settings SET
               twilio_sid = ?, twilio_auth_token = ?, twilio_phone = ?,
               gumroad_key = ?, fh_api_key = ?, fh_company_shortname = ?,
               fh_auto_respond_faq = ?, fh_auto_request_reviews = ?,
               fh_review_delay_days = ?, fh_no_show_followup = ?,
               tone_preference = ?, auto_classify = ?,
               auto_draft = ?, notify_sms = ?, notify_email = ?,
               church_discount = ?, updated_at = datetime('now')
               WHERE user_id = ?""",
            (
                body.get("twilio_sid", ""),
                body.get("twilio_auth_token", ""),
                body.get("twilio_phone", ""),
                body.get("gumroad_key", ""),
                body.get("fh_api_key", ""),
                body.get("fh_company_shortname", ""),
                int(body.get("fh_auto_respond_faq", True)),
                int(body.get("fh_auto_request_reviews", True)),
                int(body.get("fh_review_delay_days", 1)),
                int(body.get("fh_no_show_followup", True)),
                body.get("tone_preference", "professional"),
                int(body.get("auto_classify", True)),
                int(body.get("auto_draft", True)),
                int(body.get("notify_sms", False)),
                int(body.get("notify_email", True)),
                int(body.get("church_discount", False)),
                user["google_id"],
            ),
        )
    else:
        await db.execute(
            """INSERT INTO user_settings
               (user_id, twilio_sid, twilio_auth_token, twilio_phone,
                gumroad_key, fh_api_key, fh_company_shortname,
                fh_auto_respond_faq, fh_auto_request_reviews,
                fh_review_delay_days, fh_no_show_followup,
                tone_preference, auto_classify, auto_draft,
                notify_sms, notify_email, church_discount)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user["google_id"],
                body.get("twilio_sid", ""),
                body.get("twilio_auth_token", ""),
                body.get("twilio_phone", ""),
                body.get("gumroad_key", ""),
                body.get("fh_api_key", ""),
                body.get("fh_company_shortname", ""),
                int(body.get("fh_auto_respond_faq", True)),
                int(body.get("fh_auto_request_reviews", True)),
                int(body.get("fh_review_delay_days", 1)),
                int(body.get("fh_no_show_followup", True)),
                body.get("tone_preference", "professional"),
                int(body.get("auto_classify", True)),
                int(body.get("auto_draft", True)),
                int(body.get("notify_sms", False)),
                int(body.get("notify_email", True)),
                int(body.get("church_discount", False)),
            ),
        )

    await db.commit()
    await db.close()

    return {"updated": True}
