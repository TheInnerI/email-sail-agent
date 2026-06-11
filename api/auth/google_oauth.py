"""
Email Sail Agent — Google OAuth2 Authentication
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from api.config import settings

logger = logging.getLogger("email-sail.auth")

router = APIRouter()

# In-memory session store (use Redis in production)
_sessions = {}

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
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


def _generate_session_id() -> str:
    import secrets
    return secrets.token_urlsafe(32)


def _get_session(request: Request) -> dict | None:
    sid = request.cookies.get("email_sail_session")
    if sid:
        return _sessions.get(sid)
    return None


def _require_session(request: Request) -> dict:
    session = _get_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session


@router.get("/login")
async def login():
    """Redirect user to Google OAuth2 consent screen."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth2 callback."""
    import httpx

    error = request.query_params.get("error")
    if error:
        logger.error("OAuth error: %s", error)
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    # Exchange code for tokens
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        if token_resp.status_code != 200:
            logger.error("Token exchange failed: %s", token_resp.text)
            raise HTTPException(status_code=400, detail="Token exchange failed")
        tokens = token_resp.json()

        # Get user info
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        user_info = user_resp.json()

    # Create session
    session_id = _generate_session_id()
    _sessions[session_id] = {
        "user_id": user_info["id"],
        "email": user_info["email"],
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_expiry": tokens.get("expires_in", 3600),
    }

    # Store in database
    from api.database import get_db
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO users (google_id, email, name, picture, access_token, refresh_token, token_expiry, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            user_info["id"],
            user_info["email"],
            user_info.get("name", ""),
            user_info.get("picture", ""),
            tokens["access_token"],
            tokens.get("refresh_token", ""),
            str(tokens.get("expires_in", 3600)),
        ),
    )
    await db.commit()
    await db.close()

    # Redirect to dashboard with session cookie
    response = RedirectResponse(url="/dashboard")
    response.set_cookie(
        key="email_sail_session",
        value=session_id,
        httponly=True,
        max_age=86400 * 7,  # 7 days
        samesite="lax",
    )
    logger.info("User %s logged in successfully", user_info["email"])
    return response


@router.get("/logout")
async def logout():
    """Clear session and logout."""
    response = RedirectResponse(url="/")
    response.delete_cookie("email_sail_session")
    return response


@router.get("/me")
async def me(request: Request):
    """Get current user info."""
    session = _require_session(request)
    return {
        "email": session["email"],
        "name": session["name"],
        "picture": session["picture"],
    }


def get_current_user(request: Request) -> dict:
    """Dependency to get current user from session."""
    return _require_session(request)
