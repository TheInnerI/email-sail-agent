"""
Email Sail Agent — Dashboard Routes
"""

import logging

from fastapi import APIRouter, Request, HTTPException

from api.routes.auth import require_user, _get_session
from api.main import respond

logger = logging.getLogger("email-sail.dashboard")
router = APIRouter()


@router.get("/")
async def home(request: Request):
    """Home page — redirect to dashboard if logged in, else show landing."""
    session = _get_session(request)
    if session:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard")
    return respond(request, "landing.html")


@router.get("/dashboard")
async def dashboard(request: Request):
    """Main dashboard."""
    user = require_user(request)
    return respond(request, "dashboard.html", {
        "user": user,
        "page": "dashboard",
    })


@router.get("/inbox")
async def inbox(request: Request):
    """Inbox view."""
    user = require_user(request)
    return respond(request, "inbox.html", {
        "user": user,
        "page": "inbox",
    })


@router.get("/drafts")
async def drafts_page(request: Request):
    """Draft review page."""
    user = require_user(request)
    return respond(request, "draft_review.html", {
        "user": user,
        "page": "drafts",
    })


@router.get("/calendar")
async def calendar_page(request: Request):
    """Calendar/scheduling page."""
    user = require_user(request)
    return respond(request, "calendar.html", {
        "user": user,
        "page": "calendar",
    })


@router.get("/crm")
async def crm_page(request: Request):
    """CRM page."""
    user = require_user(request)
    return respond(request, "crm.html", {
        "user": user,
        "page": "crm",
    })


@router.get("/settings")
async def settings_page(request: Request):
    """Settings page."""
    user = require_user(request)
    return respond(request, "settings.html", {
        "user": user,
        "page": "settings",
    })
