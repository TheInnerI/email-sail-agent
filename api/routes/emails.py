"""
Email Sail Agent — Email API Routes
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query

from api.routes.auth import require_user
from api.services.gmail_service import GmailService
from api.services.classifier import classify_email, get_category_label, get_category_color
from api.database import get_db

logger = logging.getLogger("email-sail.emails")
router = APIRouter()


@router.get("/list")
async def list_emails(
    request: Request,
    category: Optional[str] = Query(None),
    limit: int = Query(25, le=100),
):
    """List emails, optionally filtered by category."""
    user = require_user(request)
    gmail = GmailService(user["access_token"])

    try:
        if category:
            label_name = get_category_label(category)
            # First ensure label exists
            labels = await gmail.list_labels()
            label_id = None
            for label in labels:
                if label["name"] == label_name:
                    label_id = label["id"]
                    break

            if not label_id:
                # Create the label
                new_label = await gmail.create_label(label_name, get_category_color(category))
                label_id = new_label["id"]

            messages = await gmail.list_messages(label_ids=[label_id], max_results=limit)
        else:
            messages = await gmail.list_messages(max_results=limit)

        # Fetch full message details
        emails = []
        for msg in messages[:limit]:
            try:
                full_msg = await gmail.get_message(msg["id"])
                parsed = GmailService.parse_message(full_msg)
                emails.append(parsed)
            except Exception as e:
                logger.warning("Failed to fetch message %s: %s", msg["id"], e)

        return {"emails": emails, "count": len(emails)}
    except Exception as e:
        logger.error("Error listing emails: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{message_id}")
async def get_email(request: Request, message_id: str):
    """Get a single email by ID."""
    user = require_user(request)
    gmail = GmailService(user["access_token"])

    try:
        msg = await gmail.get_message(message_id)
        parsed = GmailService.parse_message(msg)

        # Classify
        classification = classify_email(parsed["subject"], parsed["body"], parsed["from_email"])
        parsed["classification"] = classification

        return parsed
    except Exception as e:
        logger.error("Error fetching email %s: %s", message_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{message_id}/classify")
async def classify_email_route(request: Request, message_id: str):
    """Classify an email and apply the appropriate Gmail label."""
    user = require_user(request)
    gmail = GmailService(user["access_token"])

    try:
        msg = await gmail.get_message(message_id)
        parsed = GmailService.parse_message(msg)

        # Classify
        result = classify_email(parsed["subject"], parsed["body"], parsed["from_email"])
        category = result["category"]
        label_name = get_category_label(category)

        # Ensure label exists
        labels = await gmail.list_labels()
        label_id = None
        for label in labels:
            if label["name"] == label_name:
                label_id = label["id"]
                break

        if not label_id:
            new_label = await gmail.create_label(label_name, get_category_color(category))
            label_id = new_label["id"]

        # Apply label
        await gmail.modify_message(message_id, add_labels=[label_id])

        # Store in local DB
        db = await get_db()
        await db.execute(
            """INSERT OR REPLACE INTO email_threads
               (user_id, gmail_thread_id, gmail_message_id, sender_name, sender_email,
                subject, snippet, category, confidence, received_at, classified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                user["google_id"],
                parsed["thread_id"],
                message_id,
                parsed["from_name"],
                parsed["from_email"],
                parsed["subject"],
                parsed["snippet"],
                category,
                result["confidence"],
                parsed["date"],
            ),
        )
        await db.commit()
        await db.close()

        return {
            "classified": True,
            "category": category,
            "label": label_name,
            "confidence": result["confidence"],
            "reason": result["reason"],
        }
    except Exception as e:
        logger.error("Error classifying email %s: %s", message_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{message_id}/send")
async def send_email(
    request: Request,
    message_id: str,
):
    """Send an approved email response."""
    user = require_user(request)
    body = await request.json()

    to = body.get("to", "")
    subject = body.get("subject", "")
    content = body.get("body", "")
    thread_id = body.get("thread_id")

    if not to or not subject or not content:
        raise HTTPException(status_code=400, detail="Missing to, subject, or body")

    gmail = GmailService(user["access_token"])

    try:
        result = await gmail.send_message(to, subject, content, thread_id)

        # Log to CRM
        db = await get_db()
        await db.execute(
            """INSERT INTO crm_interactions (user_id, type, subject, notes, created_at)
               VALUES (?, 'email_sent', ?, ?, datetime('now'))""",
            (user["google_id"], subject, f"Sent to {to}"),
        )
        await db.commit()
        await db.close()

        return {"sent": True, "message_id": result.get("id"), "thread_id": result.get("threadId")}
    except Exception as e:
        logger.error("Error sending email: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-all")
async def classify_all_emails(request: Request):
    """Classify all unread emails in the inbox."""
    user = require_user(request)
    gmail = GmailService(user["access_token"])

    try:
        messages = await gmail.list_messages(query="is:unread", max_results=50)
        results = []

        for msg in messages:
            try:
                full_msg = await gmail.get_message(msg["id"])
                parsed = GmailService.parse_message(full_msg)
                classification = classify_email(parsed["subject"], parsed["body"], parsed["from_email"])

                # Apply label
                category = classification["category"]
                label_name = get_category_label(category)
                labels = await gmail.list_labels()
                label_id = None
                for label in labels:
                    if label["name"] == label_name:
                        label_id = label["id"]
                        break
                if not label_id:
                    new_label = await gmail.create_label(label_name, get_category_color(category))
                    label_id = new_label["id"]

                await gmail.modify_message(msg["id"], add_labels=[label_id])

                results.append({
                    "message_id": msg["id"],
                    "subject": parsed["subject"],
                    "category": category,
                    "confidence": classification["confidence"],
                })
            except Exception as e:
                logger.warning("Failed to classify %s: %s", msg["id"], e)

        return {"classified": len(results), "results": results}
    except Exception as e:
        logger.error("Error in classify-all: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
