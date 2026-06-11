"""
Email Sail Agent — Auth Routes
"""

import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from api.config import settings

logger = logging.getLogger("email-sail.auth")
router = APIRouter()

# In-memory session store
_sessions: dict[str, dict] = {}

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _new_session_id() -> str:
    return secrets.token_urlsafe(32)


def _get_session(request: Request) -> dict | None:
    sid = request.cookies.get("email_sail_session")
    if sid and sid in _sessions:
        return _sessions[sid]
    return None


def require_user(request: Request) -> dict:
    """Get current user or raise 401."""
    session = _get_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session


@router.get("/login")
async def login():
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def callback(request: Request):
    import httpx

    error = request.query_params.get("error")
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")
        tokens = token_resp.json()

        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")
        info = user_resp.json()

    sid = _new_session_id()
    _sessions[sid] = {
        "google_id": info["id"],
        "email": info["email"],
        "name": info.get("name", ""),
        "picture": info.get("picture", ""),
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
    }

    # Persist to DB
    from api.database import get_db
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO users
           (google_id, email, name, picture, access_token, refresh_token, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
        (info["id"], info["email"], info.get("name", ""),
         info.get("picture", ""), tokens["access_token"],
         tokens.get("refresh_token", "")),
    )
    await db.commit()
    await db.close()

    resp = RedirectResponse(url="/dashboard")
    resp.set_cookie("email_sail_session", sid, httponly=True, max_age=604800, samesite="lax")
    logger.info("Login: %s", info["email"])
    return resp


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/")
    resp.delete_cookie("email_sail_session")
    return resp


@router.get("/me")
async def me(request: Request):
    user = require_user(request)
    return {"email": user["email"], "name": user["name"], "picture": user["picture"]}
