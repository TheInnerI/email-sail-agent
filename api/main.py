"""
Email Sail Agent — Main FastAPI Application
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from api.config import settings
from api.database import init_db
from api.templates import respond
from api.routes import auth, dashboard, emails, drafts, calendar, sms, crm, settings as settings_routes
from api.routes.fareharbor import router as fh_router, webhook_router as fh_webhook_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.APP_DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("email-sail")

# Create app
app = FastAPI(
    title="Email Sail Agent",
    description="⛵ Your email command center. Sort, draft, book, text, and retain revenue.",
    version="1.0.0",
)

# Create data directory
Path("data").mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Initialize database on startup
@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("⛵ Email Sail Agent initialized")

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(emails.router, prefix="/api/emails", tags=["emails"])
app.include_router(drafts.router, prefix="/api/drafts", tags=["drafts"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(sms.router, prefix="/api/sms", tags=["sms"])
app.include_router(crm.router, prefix="/api/crm", tags=["crm"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["settings"])
app.include_router(fh_router, prefix="/api/fareharbor", tags=["fareharbor"])
app.include_router(fh_webhook_router, prefix="/webhooks/fareharbor", tags=["fareharbor-webhooks"])


# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "email-sail-agent",
        "version": "1.0.0",
        "time": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
