"""
Email Sail Agent — SQLite Database
"""

import aiosqlite
import logging
from api.config import settings

logger = logging.getLogger("email-sail.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    name TEXT,
    picture TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    gmail_thread_id TEXT NOT NULL,
    gmail_message_id TEXT NOT NULL,
    sender_name TEXT,
    sender_email TEXT,
    subject TEXT,
    snippet TEXT,
    category TEXT DEFAULT 'unclassified',
    confidence REAL DEFAULT 0.0,
    is_read INTEGER DEFAULT 0,
    is_starred INTEGER DEFAULT 0,
    received_at TEXT,
    classified_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    thread_id INTEGER,
    gmail_message_id TEXT,
    google_doc_id TEXT,
    google_doc_url TEXT,
    subject TEXT,
    body TEXT,
    tone TEXT DEFAULT 'professional',
    status TEXT DEFAULT 'pending',
    model_used TEXT DEFAULT 'template',
    ai_generated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    sent_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (thread_id) REFERENCES email_threads(id)
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    thread_id INTEGER,
    customer_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    event_id TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sms_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    thread_id INTEGER,
    to_number TEXT NOT NULL,
    from_number TEXT NOT NULL,
    body TEXT,
    twilio_sid TEXT,
    direction TEXT DEFAULT 'outbound',
    status TEXT DEFAULT 'queued',
    sent_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS crm_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT,
    email TEXT,
    phone TEXT,
    status TEXT DEFAULT 'new',
    total_revenue REAL DEFAULT 0.0,
    last_contact TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS crm_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    type TEXT NOT NULL,
    subject TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES crm_contacts(id)
);

CREATE TABLE IF NOT EXISTS revenue_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    gumroad_product_id TEXT,
    gumroad_product_name TEXT,
    customer_email TEXT,
    amount REAL,
    status TEXT DEFAULT 'new',
    detected_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    twilio_sid TEXT DEFAULT '',
    twilio_auth_token TEXT DEFAULT '',
    twilio_phone TEXT DEFAULT '',
    gumroad_key TEXT DEFAULT '',
    fh_api_key TEXT DEFAULT '',
    fh_company_shortname TEXT DEFAULT '',
    fh_auto_respond_faq INTEGER DEFAULT 1,
    fh_auto_request_reviews INTEGER DEFAULT 1,
    fh_review_delay_days INTEGER DEFAULT 1,
    fh_no_show_followup INTEGER DEFAULT 1,
    tier TEXT DEFAULT 'free',
    preferred_model TEXT DEFAULT '',
    business_info TEXT DEFAULT '',
    signature TEXT DEFAULT '',
    tone_preference TEXT DEFAULT 'professional',
    auto_classify INTEGER DEFAULT 1,
    auto_draft INTEGER DEFAULT 1,
    notify_sms INTEGER DEFAULT 0,
    notify_email INTEGER DEFAULT 1,
    church_discount INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_threads_user ON email_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_threads_category ON email_threads(category);
CREATE INDEX IF NOT EXISTS idx_drafts_user ON drafts(user_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_crm_email ON crm_contacts(user_id, email);
CREATE INDEX IF NOT EXISTS idx_revenue_status ON revenue_alerts(user_id, status);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize the database schema."""
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    await db.executescript(SCHEMA)
    await db.commit()
    await db.close()
    logger.info("Database initialized at %s", settings.DATABASE_PATH)
