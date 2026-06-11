"""
Email Sail Agent — Gmail Service
"""

import logging
import base64
import re
from typing import Optional
from datetime import datetime

import httpx

from api.config import settings

logger = logging.getLogger("email-sail.gmail")

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailService:
    """Gmail API wrapper using raw httpx (avoids google-api-python-client weight)."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def _get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GMAIL_API_BASE}{path}", headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, body: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{GMAIL_API_BASE}{path}", headers=self.headers, json=body, timeout=30)
            resp.raise_for_status()
            return resp.json()

    async def list_labels(self) -> list[dict]:
        """Get all Gmail labels."""
        data = await self._get("/labels")
        return data.get("labels", [])

    async def create_label(self, name: str, color: str = None) -> dict:
        """Create a new Gmail label."""
        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        if color:
            body["color"] = {"backgroundColor": color, "textColor": "#ffffff"}
        return await self._post("/labels", body)

    async def list_messages(self, label_ids: list[str] = None, max_results: int = 25, query: str = None) -> list[dict]:
        """List messages, optionally filtered by label or query."""
        params = {"maxResults": max_results}
        if label_ids:
            params["labelIds"] = label_ids
        if query:
            params["q"] = query
        data = await self._get("/messages", params=params)
        return data.get("messages", [])

    async def get_message(self, msg_id: str) -> dict:
        """Get full message details."""
        return await self._get(f"/messages/{msg_id}", params={"format": "full"})

    async def get_thread(self, thread_id: str) -> dict:
        """Get full thread."""
        return await self._get(f"/threads/{thread_id}", params={"format": "full"})

    async def modify_message(self, msg_id: str, add_labels: list[str] = None, remove_labels: list[str] = None) -> dict:
        """Add/remove labels from a message."""
        body = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels
        return await self._post(f"/messages/{msg_id}/modify", body)

    async def send_message(self, to: str, subject: str, body: str, thread_id: str = None) -> dict:
        """Send an email."""
        from email.mime.text import MIMEText
        import base64

        msg = MIMEText(body, "html")
        msg["to"] = to
        msg["subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_string().encode()).decode()
        payload = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        return await self._post("/messages/send", payload)

    async def trash_message(self, msg_id: str) -> dict:
        return await self._post(f"/messages/{msg_id}/trash", {})

    @staticmethod
    def parse_message(msg: dict) -> dict:
        """Parse a Gmail message into a clean dict."""
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

        # Extract body
        body = ""
        payload = msg.get("payload", {})
        if payload.get("mimeType") == "text/plain":
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    body_data = part.get("body", {}).get("data", "")
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
                        break

        # Clean body (remove signatures, quoted replies)
        body = re.sub(r"On\s+.+\s+wrote:.*", "", body, flags=re.DOTALL)
        body = re.sub(r"--+\n.*", "", body, flags=re.DOTALL)
        body = body.strip()

        return {
            "id": msg.get("id", ""),
            "thread_id": msg.get("threadId", ""),
            "subject": headers.get("subject", "(No Subject)"),
            "from_name": GmailService._extract_name(headers.get("from", "")),
            "from_email": GmailService._extract_email(headers.get("from", "")),
            "to": headers.get("to", ""),
            "date": headers.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body[:5000],  # Limit body size
            "labels": msg.get("labelIds", []),
            "is_unread": "UNREAD" in msg.get("labelIds", []),
        }

    @staticmethod
    def _extract_name(from_header: str) -> str:
        match = re.match(r"^(.+?)\s*<", from_header)
        return match.group(1).strip() if match else from_header

    @staticmethod
    def _extract_email(from_header: str) -> str:
        match = re.search(r"<(.+?)>", from_header)
        return match.group(1) if match else from_header
