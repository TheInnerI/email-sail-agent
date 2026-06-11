# ⛵ Email Sail Agent

> **Escape email jail.** Auto-sort Gmail, draft responses, book appointments, text customers, and retain revenue — all from one click.

Email Sail Agent is an email command center for small business owners, freelancers, coaches, and tour operators. It connects to your Gmail, Google Calendar, Google Docs, Google Sheets, Twilio, and FareHarbor to automate the repetitive parts of email management while keeping you in control of every send.

**Launch format:** Chrome Extension + hosted web app. Docker Compose for self-hosted.

**Live demo:** https://email-sail.innerinetcompany.com (coming soon)

---

## Table of Contents

- [Features](#features)
- [Product Tiers](#product-tiers)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Keys & Credentials](#api-keys--credentials)
  - [Google OAuth2](#1-google-oauth2-gmail-docs-calendar-sheets)
  - [Twilio (SMS + Voice)](#2-twilio-sms--voice)
  - [Gumroad (Revenue Signals)](#3-gumroad-revenue-signals)
  - [FareHarbor (Booking Integration)](#4-fareharbor-booking-integration)
- [Installation](#installation)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Manual Install](#manual-install)
  - [systemd Service](#systemd-service)
- [Chrome Extension](#chrome-extension)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Gmail Classification Categories](#gmail-classification-categories)
- [FareHarbor Integration](#fareharbor-integration)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Feature | Free | Starter $99 | Pro $299 | Full $499 |
|---|:---:|:---:|:---:|:---:|
| Gmail auto-sort + 7 labels | ✅ | ✅ | ✅ | ✅ |
| Dashboard + inbox overview | ✅ | ✅ | ✅ | ✅ |
| AI response drafts in Google Docs | | ✅ | ✅ | ✅ |
| One-click send after approval | | ✅ | ✅ | ✅ |
| Google Sheet CRM auto-logging | | ✅ | ✅ | ✅ |
| Chrome Extension | | ✅ | ✅ | ✅ |
| Google Calendar booking | | | ✅ | ✅ |
| Twilio SMS to customers | | | ✅ | ✅ |
| Revenue retention alerts (Gumroad) | | | ✅ | ✅ |
| Custom email templates (10) | | | ✅ | ✅ |
| Docker Compose self-host | | | ✅ | ✅ |
| Twilio Voice calls | | | | ✅ |
| Multi-account (3 Gmail accounts) | | | | ✅ |
| Custom AI tone training | | | | ✅ |
| Electron desktop app | | | | ✅ |
| FareHarbor booking integration | | | Read | Full |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Email Sail Agent                         │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Gmail    │───▶│ Classifier   │───▶│ Response Drafter │  │
│  │ API      │    │ (11 categories)│   │ (Google Docs)    │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│       │                │                      │             │
│       ▼                ▼                      ▼             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Calendar │    │ CRM          │    │ Twilio           │  │
│  │ API      │    │ (Sheets API) │    │ (SMS + Voice)    │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│       │                │                      │             │
│       ▼                ▼                      ▼             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │FareHarbor│    │ Gumroad      │    │ PoA Engine       │  │
│  │ API      │    │ (Revenue)    │    │ (Receipts)       │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│                                                             │
│  Backend: FastAPI + SQLite + Jinja2 + htmx                 │
│  Frontend: Server-rendered HTML (dark theme)                │
│  Browser: Chrome Extension (toolbar button)                 │
│  HTTPS: Caddy (automatic Let's Encrypt)                     │
│  Deploy: Docker Compose + systemd                           │
└─────────────────────────────────────────────────────────────┘
```

**Stack:**
- **Backend:** FastAPI (Python 3.12+)
- **Database:** SQLite (zero config, single file)
- **Templates:** Jinja2 + htmx (no build step, no Node.js)
- **Auth:** Google OAuth2 + session cookies
- **HTTPS:** Caddy (automatic Let's Encrypt)
- **Deployment:** Docker Compose or systemd

---

## Quick Start

### Docker Compose (Recommended)

```bash
# 1. Clone the repo
cd ~/Documents/TheInnerI/06_INFRASTRUCTURE/email-sail-agent

# 2. Configure environment
cp .env.example .env
nano .env   # Add your API keys (see below)

# 3. Launch
docker compose up -d

# 4. Open in browser
open http://localhost:8090
```

### Manual Install

```bash
# 1. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env

# 4. Run
python -m uvicorn api.main:app --host 0.0.0.0 --port 8090
```

---

## API Keys & Credentials

Email Sail connects to 4 external services. Here's where to get each API key:

### 1. Google OAuth2 (Gmail, Docs, Calendar, Sheets)

**What it powers:** Email reading/sending, draft creation, appointment booking, CRM logging.

**Get it:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project: `email-sail-agent`
3. **Enable these APIs** (APIs & Services → Library):
   - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
   - [Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)
   - [Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
   - [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
4. **OAuth consent screen** (APIs & Services → OAuth consent screen):
   - User type: External
   - App name: `Email Sail Agent`
   - Scopes — add these:
     - `openid`
     - `userinfo.email`
     - `userinfo.profile`
     - `gmail.readonly`
     - `gmail.modify`
     - `gmail.send`
     - `documents`
     - `calendar`
     - `calendar.events`
     - `spreadsheets`
5. **Credentials** (APIs & Services → Credentials → Create → OAuth client ID):
   - Application type: Web application
   - Authorized redirect URIs:
     - `http://localhost:8090/auth/callback` (local dev)
     - `https://email-sail.innerinetcompany.com/auth/callback` (production)
6. Copy **Client ID** and **Client Secret**

**Env vars:**
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8090/auth/callback
```

**Docs:** https://developers.google.com/identity/protocols/oauth2

---

### 2. Twilio (SMS + Voice)

**What it powers:** Text customers, click-to-call, appointment reminders.

**Get it:**
1. Sign up at [twilio.com/try-twilio](https://www.twilio.com/try-twilio) (free trial = $15 credit)
2. Get a phone number: [Console → Phone Numbers → Buy a Number](https://console.twilio.com/us1/develop/phone-numbers/manage/search)
   - Any local number works (~$1/month)
   - Make sure it has SMS + Voice capability
3. Find your credentials: [Console Dashboard](https://console.twilio.com/)
   - Account SID (starts with `AC...`)
   - Auth Token (click "Show")

**Env vars:**
```
TWILIO_ACCOUNT_sid=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+15551234567
```

**Pricing:**
- SMS: ~$0.0075/message (US)
- Voice: ~$0.013/minute (US)
- Phone number: ~$1/month
- User pays actual usage — we don't markup

**Docs:** https://www.twilio.com/docs/sms/api | https://www.twilio.com/docs/voice/api

---

### 3. Gumroad (Revenue Signals)

**What it powers:** Detect abandoned carts, failed payments, expiring licenses → draft recovery emails.

**Get it:**
1. Go to [Gumroad → Settings → Advanced → Applications](https://gumroad.com/settings/advanced#application_form)
2. Create a new application
3. Copy the **Access Token**

**Env var:**
```
GUMROAD_API_KEY=your-gumroad-access-token
```

**Docs:** https://gumroad.com/api

---

### 4. FareHarbor (Booking Integration)

**What it powers:** Tour/activity booking management. Detect booking changes, cancellations, no-shows. Auto-draft responses with booking context.

**Get it:**
1. Email `support@fareharbor.com` with:
   > "Hi, I'm building an email management tool for tour operators called Email Sail Agent. I'd like to integrate with the FareHarbor External API to: (1) look up bookings by customer email, (2) detect booking changes and cancellations, (3) create bookings from email inquiries, (4) receive webhooks for no-shows. Can you grant API access?"
2. They'll review and provide an API key + company shortname
3. This is for **Pro** (read-only) and **Full** (read-write + webhooks) tiers

**Env vars:**
```
FAREHARBOR_API_KEY=your-fareharbor-api-key
FAREHARBOR_COMPANY_SHORTNAME=your-company-shortname
```

**Docs:** https://developer.fareharbor.com/api/external/v1/

---

## Installation

### Docker Compose (Recommended)

```bash
cd ~/Documents/TheInnerI/06_INFRASTRUCTURE/email-sail-agent

# Configure
cp .env.example .env
nano .env   # Add your API keys

# Launch (includes Caddy for HTTPS)
docker compose up -d

# Check health
curl http://localhost:8090/health

# View logs
docker compose logs -f email-sail
```

**Services:**
- `email-sail` — FastAPI app on port 8090
- `caddy` — HTTPS reverse proxy on ports 80/443

### Manual Install

```bash
# Python 3.12+ required
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env

# Run
python -m uvicorn api.main:app --host 0.0.0.0 --port 8090
```

### systemd Service

```bash
# Copy service file
cp email-sail.service /etc/systemd/system/email-sail-agent.service
sudo systemctl daemon-reload
sudo systemctl enable email-sail-agent
sudo systemctl start email-sail-agent

# Check status
sudo systemctl status email-sail-agent
journalctl -u email-sail-agent -f
```

---

## Chrome Extension

The Chrome Extension adds a **⛵ Sail** button to your Gmail toolbar. One click to classify, draft, or check booking info.

### Install (Development)

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `chrome-extension/` folder
5. The ⛵ icon appears in your toolbar

### Install (Production)

1. Zip the `chrome-extension/` folder
2. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
3. Upload zip → submit for review (1-3 days)
4. Users install from Chrome Web Store

### How It Works

1. Click the ⛵ icon → popup opens
2. Enter your server URL (e.g., `https://email-sail.innerinetcompany.com`)
3. Click **Connect** → verifies server health
4. Click **Connect Gmail** → Google OAuth2 flow
5. Now when you open an email in Gmail:
   - A **⛵ Sail** button appears in the toolbar
   - Click it to classify the email or draft a response
   - If FareHarbor is configured, booking context appears

---

## Configuration

All configuration is via environment variables (`.env` file):

```bash
# App
SECRET_KEY=change-this-to-a-random-secret-key
APP_HOST=0.0.0.0
APP_PORT=8090
APP_DEBUG=false

# Google OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8090/auth/callback

# Twilio
TWILIO_ACCOUNT_sid=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+15551234567

# Gumroad
GUMROAD_API_KEY=your-gumroad-access-token

# FareHarbor
FAREHARBOR_API_KEY=your-fareharbor-api-key
FAREHARBOR_COMPANY_SHORTNAME=your-company-shortname

# Database
DATABASE_PATH=data/email_sail.db

# PoA Engine (optional)
POA_ENGINE_URL=http://localhost:8000

# MIO Observer (optional)
MIO_OBSERVER_URL=http://localhost:8787
```

---

## API Reference

### Auth

| Method | Path | Description |
|---|---|---|
| GET | `/auth/login` | Redirect to Google OAuth2 |
| GET | `/auth/callback` | OAuth2 callback |
| GET | `/auth/logout` | Clear session |
| GET | `/auth/me` | Current user info |

### Emails

| Method | Path | Description |
|---|---|---|
| GET | `/api/emails/list` | List emails (optional `?category=` filter) |
| GET | `/api/emails/{id}` | Get email details + classification |
| POST | `/api/emails/{id}/classify` | Classify + apply Gmail label |
| POST | `/api/emails/{id}/send` | Send approved email |
| POST | `/api/emails/classify-all` | Classify all unread emails |

### Drafts

| Method | Path | Description |
|---|---|---|
| POST | `/api/drafts/create` | Create draft in Google Docs |
| GET | `/api/drafts/list` | List pending drafts |
| POST | `/api/drafts/{id}/approve` | Approve + send draft |
| POST | `/api/drafts/{id}/dismiss` | Dismiss without sending |

### Calendar

| Method | Path | Description |
|---|---|---|
| GET | `/api/calendar/events` | Get events (optional `?days=7`) |
| GET | `/api/calendar/free-slots` | Find available time slots |
| POST | `/api/calendar/book` | Book an appointment |

### SMS

| Method | Path | Description |
|---|---|---|
| POST | `/api/sms/send` | Send SMS via Twilio |
| POST | `/api/sms/draft` | Draft SMS (returns text, doesn't send) |

### CRM

| Method | Path | Description |
|---|---|---|
| GET | `/api/crm/contacts` | List CRM contacts |
| POST | `/api/crm/create-sheet` | Create Google Sheet CRM |
| POST | `/api/crm/upsert-contact` | Add/update contact |
| POST | `/api/crm/log-interaction` | Log email/SMS/call |

### FareHarbor

| Method | Path | Description |
|---|---|---|
| GET | `/api/fareharbor/items` | List bookable items/tours |
| GET | `/api/fareharbor/items/{id}/availabilities` | Get available slots |
| GET | `/api/fareharbor/bookings` | List bookings |
| GET | `/api/fareharbor/bookings/today` | Today's bookings |
| POST | `/api/fareharbor/bookings` | Create booking |
| DELETE | `/api/fareharbor/bookings/{id}` | Cancel booking |
| POST | `/api/fareharbor/bookings/{id}/note` | Update booking note |
| GET | `/api/fareharbor/lookup?email=` | Look up booking by email |
| POST | `/webhooks/fareharbor/` | Webhook handler |

### Settings

| Method | Path | Description |
|---|---|---|
| GET | `/api/settings/` | Get user settings |
| POST | `/api/settings/` | Update user settings |

---

## Gmail Classification Categories

Emails are automatically sorted into 7 labels:

| Category | Label | Color | Triggers |
|---|---|---|---|
| 🔴 Urgent | ⛵ Urgent | Red | "urgent", "asap", "today", "emergency" |
| 🟡 Customer Inquiry | ⛵ Customer Inquiry | Yellow | "question", "interested", "pricing", "quote" |
| 🟢 Invoice/Payment | ⛵ Invoice/Payment | Green | "invoice", "payment", "receipt", "billing" |
| 🟣 Booking Request | ⛵ Booking Request | Purple | "schedule", "book", "appointment", "available" |
| 🟠 Revenue Alert | ⛵ Revenue Alert | Orange | "abandoned cart", "failed payment", "expired" |
| 🔵 Newsletter | ⛵ Newsletter | Blue | "newsletter", "unsubscribe", "digest" |
| ⚪ Low Priority | ⛵ Low Priority | Gray | "won", "lottery", "click here", "free money" |

**FareHarbor categories** (when FH is configured):

| Category | Label | Color | Triggers |
|---|---|---|---|
| 🎫 FH: Change | 🎫 FH: Change | Amber | "change", "reschedule", "move my booking" |
| 🎫 FH: Cancel | 🎫 FH: Cancel | Red | "cancel", "can't make it", "won't be able" |
| 🎫 FH: FAQ | 🎫 FH: FAQ | Violet | "what to bring", "where to meet", "parking" |
| 🎫 FH: Group | 🎫 FH: Group | Cyan | "group", "private", "team building", "corporate" |

---

## FareHarbor Integration

For tour operators and activity providers using [FareHarbor](https://fareharbor.com):

**What it does:**
- Detects booking change/cancellation requests in email
- Looks up booking details via FH API
- Checks availability for rescheduling
- Drafts responses with booking context
- Creates bookings from email inquiries
- Handles no-show follow-up (via webhook)
- Requests reviews post-trip

**Setup:**
1. Get API access: email `support@fareharbor.com`
2. Add `FAREHARBOR_API_KEY` and `FAREHARBOR_COMPANY_SHORTname` to `.env`
3. Configure webhook URL in FareHarbor: `https://your-domain.com/webhooks/fareharbor/`

**Docs:** [`email-sail-fareharbor-integration.md`](../07_BUSINESS/products/email-sail-fareharbor-integration.md)

---

## Deployment

### Production Checklist

- [ ] Google Cloud project created + APIs enabled
- [ ] OAuth consent screen configured
- [ ] OAuth credentials created (Client ID + Secret)
- [ ] Twilio account + phone number
- [ ] Gumroad API key (optional)
- [ ] FareHarbor API access (optional)
- [ ] Domain DNS pointed to server
- [ ] `.env` configured with all credentials
- [ ] Docker Compose running
- [ ] Caddy HTTPS working
- [ ] Chrome Extension packaged

### Server Requirements

- **OS:** Ubuntu 22.04+ / Debian 12+
- **RAM:** 512MB minimum
- **Storage:** 1GB minimum
- **Ports:** 80, 443, 8090
- **Software:** Docker + Docker Compose

### Nginx Alternative (without Caddy)

```nginx
server {
    listen 80;
    server_name email-sail.innerinetcompany.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name email-sail.innerinetcompany.com;

    ssl_certificate /etc/letsencrypt/live/email-sail.innerinetcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/email-sail.innerinetcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Troubleshooting

### Port 8090 already in use
```bash
# Find what's using it
lsof -i :8090
# Kill it
kill <PID>
# Or if it's systemd
sudo systemctl stop email-sail-agent
```

### Google OAuth redirect mismatch
- Make sure `GOOGLE_REDIRECT_URI` in `.env` matches exactly what's in Google Cloud Console
- Include trailing slashes if present
- For local dev: `http://localhost:8090/auth/callback`
- For production: `https://your-domain.com/auth/callback`

### Gmail API rate limits
- Gmail API: 100 requests/100 seconds per user
- If you hit limits, the app queues and retries automatically
- For high-volume inboxes, consider batching classification

### Twilio SMS not sending
- Check Twilio account balance (free trial = $15 credit)
- Verify phone number is SMS-capable
- Check `TWILIO_PHONE_NUMBER` includes country code (e.g., `+15551234567`)
- For production: complete Twilio business verification

### Chrome Extension can't connect
- Make sure the server URL is correct (include `http://` or `https://`)
- Check CORS: the server must allow `chrome-extension://*` origins
- For local dev: use `http://localhost:8090` (not `127.0.0.1`)

### Database locked (SQLite)
- SQLite doesn't handle concurrent writes well
- For production with multiple users, consider PostgreSQL
- For single-user: this is fine

---

## Product Tiers & Pricing

| Tier | Price | Includes |
|---|---|---|
| **Free** | $0 | Gmail sort + labels, dashboard |
| **Starter** | $99 one-time | + AI drafts, CRM, Chrome Extension |
| **Pro** | $299 one-time | + Calendar booking, SMS, revenue alerts, Docker |
| **Full** | $499 one-time | + Voice calls, multi-account, tone training, FH full |
| **Monitoring** | $11/mo or $29/mo | Weekly inbox health reports |

**Payment:** Gumroad only. No Stripe.

**Twilio costs:** User pays actual SMS/call usage. We don't markup.

**Churches/nonprofits:** 50% discount code available.

---

## Links

- **Product Spec:** [`07_BUSINESS/products/email-sail-agent-spec.md`](../07_BUSINESS/products/email-sail-agent-spec.md)
- **Agent SOUL:** [`04_SYSTEM/agents/email-sail-agent-soul.md`](../../04_SYSTEM/agents/email-sail-agent-soul.md)
- **Offer Ladder:** [`07_BUSINESS/products/_OFFER-LADDER-TEMPLATE.md`](../07_BUSINESS/products/_OFFER-LADDER-TEMPLATE.md)
- **FareHarbor Integration:** [`07_BUSINESS/products/email-sail-fareharbor-integration.md`](../07_BUSINESS/products/email-sail-fareharbor-integration.md)
- **Skill File:** [`~/.hermes/skills/devops/email-sail-agent/SKILL.md`](~/.hermes/skills/devops/email-sail-agent/SKILL.md)

## License

Inner I Network — innerinetcompany.com
