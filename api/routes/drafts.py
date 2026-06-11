"""
Email Sail Agent — Draft API Routes
"""

import logging

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user
from api.services.gmail_service import GmailService
from api.services.drafter import create_draft_in_docs
from api.services.classifier import classify_email
from api.database import get_db

logger = logging.getLogger("email-sail.drafts")
router = APIRouter()


@router.post("/create")
async def create_draft(request: Request):
    """Create a draft response for an email."""
    user = require_user(request)
    body = await request.json()

    message_id = body.get("message_id")
    tone = body.get("tone", "professional")

    if not message_id:
        raise HTTPException(status_code=400, detail="Missing message_id")

    try:
        # Fetch the email
        gmail = GmailService(user["access_token"])
        msg = await gmail.get_message(message_id)
        parsed = GmailService.parse_message(msg)

        # Classify
        classification = classify_email(parsed["subject"], parsed["body"], parsed["from_email"])

        # Get user's tier and preferred model from settings
        db = await get_db()
        cursor = await db.execute(
            "SELECT tier, preferred_model, business_info FROM user_settings WHERE user_id = ?",
            (user["google_id"],),
        )
        user_settings = await cursor.fetchone()
        await db.close()

        user_tier = user_settings["tier"] if user_settings and user_settings["tier"] else "free"
        preferred_model = user_settings["preferred_model"] if user_settings else None
        business_info = user_settings["business_info"] if user_settings else ""
        user_name = user.get("name", "")
        custom_signature = user_settings["signature"] if user_settings else ""
        # Use custom signature if provided, otherwise use user's name
        signature = custom_signature if custom_signature else user_name

        # Create draft in Google Docs (AI or template fallback)
        draft_result = await create_draft_in_docs(
            access_token=user["access_token"],
            subject=parsed["subject"],
            sender_name=parsed["from_name"],
            sender_email=parsed["from_email"],
            email_body=parsed["body"],
            category=classification["category"],
            tone=tone,
            business_info=business_info,
            tier=user_tier,
            preferred_model=preferred_model,
            user_name=signature,
        )

        # Store draft in local DB
        db = await get_db()
        await db.execute(
            """INSERT INTO drafts
               (user_id, thread_id, gmail_message_id, google_doc_id, google_doc_url,
                subject, body, tone, status, model_used, ai_generated, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, datetime('now'))""",
            (
                user["google_id"],
                parsed["thread_id"],
                message_id,
                draft_result["doc_id"],
                draft_result["doc_url"],
                parsed["subject"],
                draft_result["draft_text"],
                tone,
                draft_result.get("model_used", "template"),
                draft_result.get("ai_generated", False),
            ),
        )
        await db.commit()
        await db.close()

        return {
            "draft_created": True,
            "doc_id": draft_result["doc_id"],
            "doc_url": draft_result["doc_url"],
            "doc_title": draft_result["doc_title"],
            "category": classification["category"],
            "draft_text": draft_result["draft_text"],
            "ai_generated": draft_result.get("ai_generated", False),
            "model_used": draft_result.get("model_used", "template"),
        }
    except Exception as e:
        logger.error("Error creating draft: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_drafts(request: Request):
    """List all pending drafts."""
    user = require_user(request)
    db = await get_db()

    cursor = await db.execute(
        """SELECT * FROM drafts WHERE user_id = ? AND status = 'pending'
           ORDER BY created_at DESC LIMIT 50""",
        (user["google_id"],),
    )
    rows = await cursor.fetchall()
    await db.close()

    drafts = []
    for row in rows:
        drafts.append({
            "id": row["id"],
            "subject": row["subject"],
            "doc_url": row["google_doc_url"],
            "doc_id": row["google_doc_id"],
            "tone": row["tone"],
            "status": row["status"],
            "created_at": row["created_at"],
        })

    return {"drafts": drafts, "count": len(drafts)}


@router.post("/{draft_id}/approve")
async def approve_draft(request: Request, draft_id: int):
    """Approve and send a draft."""
    user = require_user(request)
    db = await get_db()

    # Get draft
    cursor = await db.execute(
        "SELECT * FROM drafts WHERE id = ? AND user_id = ?",
        (draft_id, user["google_id"]),
    )
    draft = await cursor.fetchone()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Get the original email to find the recipient
    gmail = GmailService(user["access_token"])
    try:
        msg = await gmail.get_message(draft["gmail_message_id"])
        parsed = GmailService.parse_message(msg)

        # Send the email
        send_result = await gmail.send_message(
            to=parsed["from_email"],
            subject=f"Re: {draft['subject']}",
            body=draft["body"],
            thread_id=draft["thread_id"],
        )

        # Update draft status
        await db.execute(
            "UPDATE drafts SET status = 'sent', sent_at = datetime('now') WHERE id = ?",
            (draft_id,),
        )
        await db.commit()

        return {"sent": True, "message_id": send_result.get("id")}
    except Exception as e:
        logger.error("Error sending draft %s: %s", draft_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.post("/{draft_id}/dismiss")
async def dismiss_draft(request: Request, draft_id: int):
    """Dismiss a draft without sending."""
    user = require_user(request)
    db = await get_db()

    await db.execute(
        "UPDATE drafts SET status = 'dismissed' WHERE id = ? AND user_id = ?",
        (draft_id, user["google_id"]),
    )
    await db.commit()
    await db.close()

    return {"dismissed": True}
