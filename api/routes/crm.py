"""
Email Sail Agent — CRM API Routes
"""

import logging

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user
from api.services.sheets_service import SheetsCRMService
from api.database import get_db

logger = logging.getLogger("email-sail.crm")
router = APIRouter()

# Store sheet IDs per user (in production, use DB)
_user_sheet_ids: dict[str, str] = {}


@router.get("/contacts")
async def get_contacts(request: Request):
    """Get all CRM contacts."""
    user = require_user(request)
    sheet_id = _user_sheet_ids.get(user["google_id"])

    if not sheet_id:
        return {"contacts": [], "sheet_url": None, "message": "No CRM sheet configured. Create one in Settings."}

    crm = SheetsCRMService(user["access_token"])
    try:
        contacts = await crm.get_all_contacts(sheet_id)
        return {"contacts": contacts, "sheet_id": sheet_id}
    except Exception as e:
        logger.error("Error fetching contacts: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-sheet")
async def create_crm_sheet(request: Request):
    """Create a new Google Sheet for CRM."""
    user = require_user(request)
    crm = SheetsCRMService(user["access_token"])

    try:
        sheet = await crm.create_crm_spreadsheet()
        _user_sheet_ids[user["google_id"]] = sheet["id"]
        return sheet
    except Exception as e:
        logger.error("Error creating CRM sheet: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upsert-contact")
async def upsert_contact(request: Request):
    """Add or update a contact."""
    user = require_user(request)
    body = await request.json()

    sheet_id = _user_sheet_ids.get(user["google_id"])
    if not sheet_id:
        raise HTTPException(status_code=400, detail="No CRM sheet configured")

    crm = SheetsCRMService(user["access_token"])
    try:
        result = await crm.upsert_contact(
            sheet_id=sheet_id,
            name=body.get("name", ""),
            email=body.get("email", ""),
            phone=body.get("phone", ""),
            status=body.get("status", "new"),
            revenue=body.get("revenue", 0.0),
            last_thread=body.get("last_thread", ""),
            notes=body.get("notes", ""),
        )
        return result
    except Exception as e:
        logger.error("Error upserting contact: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-interaction")
async def log_interaction(request: Request):
    """Log an interaction."""
    user = require_user(request)
    body = await request.json()

    sheet_id = _user_sheet_ids.get(user["google_id"])
    if not sheet_id:
        raise HTTPException(status_code=400, detail="No CRM sheet configured")

    crm = SheetsCRMService(user["access_token"])
    try:
        result = await crm.log_interaction(
            sheet_id=sheet_id,
            email=body.get("email", ""),
            interaction_type=body.get("type", "email"),
            subject=body.get("subject", ""),
            notes=body.get("notes", ""),
        )
        return result
    except Exception as e:
        logger.error("Error logging interaction: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
