"""
Email Sail Agent — Google Sheets CRM Service
"""

import logging
from typing import Optional
from datetime import datetime

import httpx

logger = logging.getLogger("email-sail.crm")

SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files"

CRM_SHEET_HEADERS = [
    "Customer Name",
    "Email",
    "Phone",
    "Status",
    "Total Revenue",
    "Last Contact",
    "Last Thread",
    "Notes",
    "Created",
]


class SheetsCRMService:
    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def create_crm_spreadsheet(self, title: str = "Email Sail CRM") -> dict:
        """Create a new Google Sheet for CRM tracking."""
        async with httpx.AsyncClient() as client:
            # Create spreadsheet
            resp = await client.post(
                SHEETS_API_BASE,
                headers=self.headers,
                json={
                    "properties": {"title": title},
                    "sheets": [{
                        "properties": {
                            "title": "Contacts",
                            "gridProperties": {"frozenRowCount": 1},
                        },
                    }],
                },
                timeout=30,
            )
            resp.raise_for_status()
            sheet = resp.json()
            sheet_id = sheet["spreadsheetId"]

            # Add headers
            await client.put(
                f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!A1:I1",
                headers=self.headers,
                json={
                    "values": [CRM_SHEET_HEADERS],
                    "majorDimension": "ROWS",
                },
                timeout=30,
            )

            # Format headers (bold)
            await client.post(
                f"{SHEETS_API_BASE}/{sheet_id}:batchUpdate",
                headers=self.headers,
                json={
                    "requests": [{
                        "repeatCell": {
                            "range": {
                                "sheetId": 0,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "textFormat": {"bold": True},
                                    "backgroundColor": {"red": 0.1, "green": 0.15, "blue": 0.25},
                                    "horizontalAlignment": "CENTER",
                                }
                            },
                            "fields": "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)",
                        }
                    }],
                },
                timeout=30,
            )

        return {
            "id": sheet_id,
            "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
            "title": title,
        }

    async def find_contact(self, sheet_id: str, email: str) -> Optional[dict]:
        """Find a contact by email."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!B:B",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            values = resp.json().get("values", [])

            for i, row in enumerate(values):
                if row and row[0].lower() == email.lower():
                    # Get full row
                    row_resp = await client.get(
                        f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!A{i+1}:I{i+1}",
                        headers=self.headers,
                        timeout=30,
                    )
                    row_data = row_resp.json().get("values", [[]])[0]
                    return {
                        "row": i + 1,
                        "name": row_data[0] if len(row_data) > 0 else "",
                        "email": row_data[1] if len(row_data) > 1 else "",
                        "phone": row_data[2] if len(row_data) > 2 else "",
                        "status": row_data[3] if len(row_data) > 3 else "new",
                        "revenue": row_data[4] if len(row_data) > 4 else "0",
                        "last_contact": row_data[5] if len(row_data) > 5 else "",
                        "last_thread": row_data[6] if len(row_data) > 6 else "",
                        "notes": row_data[7] if len(row_data) > 7 else "",
                    }
        return None

    async def upsert_contact(
        self,
        sheet_id: str,
        name: str,
        email: str,
        phone: str = "",
        status: str = "new",
        revenue: float = 0.0,
        last_thread: str = "",
        notes: str = "",
    ) -> dict:
        """Add or update a contact."""
        existing = await self.find_contact(sheet_id, email)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        row_data = [name, email, phone, status, str(revenue), now, last_thread, notes, now]

        async with httpx.AsyncClient() as client:
            if existing:
                # Update existing row
                row_num = existing["row"]
                await client.put(
                    f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!A{row_num}:I{row_num}",
                    headers=self.headers,
                    json={"values": [row_data], "majorDimension": "ROWS"},
                    timeout=30,
                )
                return {"action": "updated", "row": row_num}
            else:
                # Append new row
                await client.post(
                    f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!A:I:append",
                    headers=self.headers,
                    json={"values": [row_data], "majorDimension": "ROWS"},
                    params={"valueInputOption": "USER_ENTERED"},
                    timeout=30,
                )
                return {"action": "created"}

    async def log_interaction(
        self,
        sheet_id: str,
        email: str,
        interaction_type: str,
        subject: str = "",
        notes: str = "",
    ) -> dict:
        """Log an interaction (email sent, SMS, call) against a contact."""
        contact = await self.find_contact(sheet_id, email)
        if not contact:
            return {"error": "Contact not found"}

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        interaction_note = f"[{now}] {interaction_type}: {subject}"
        if notes:
            interaction_note += f" — {notes}"

        # Append to existing notes
        existing_notes = contact.get("notes", "")
        updated_notes = f"{existing_notes}\n{interaction_note}" if existing_notes else interaction_note

        # Update the contact row
        row_num = contact["row"]
        row_data = [
            contact.get("name", ""),
            contact.get("email", ""),
            contact.get("phone", ""),
            contact.get("status", "new"),
            contact.get("revenue", "0"),
            now,
            contact.get("last_thread", ""),
            updated_notes,
            contact.get("created", now),
        ]

        async with httpx.AsyncClient() as client:
            await client.put(
                f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!A{row_num}:I{row_num}",
                headers=self.headers,
                json={"values": [row_data], "majorDimension": "ROWS"},
                timeout=30,
            )

        return {"action": "logged", "row": row_num}

    async def get_all_contacts(self, sheet_id: str) -> list[dict]:
        """Get all contacts from the CRM."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SHEETS_API_BASE}/{sheet_id}/values/Contacts!A2:I",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            values = resp.json().get("values", [])

        contacts = []
        for i, row in enumerate(values):
            if row:
                contacts.append({
                    "row": i + 2,
                    "name": row[0] if len(row) > 0 else "",
                    "email": row[1] if len(row) > 1 else "",
                    "phone": row[2] if len(row) > 2 else "",
                    "status": row[3] if len(row) > 3 else "new",
                    "revenue": row[4] if len(row) > 4 else "0",
                    "last_contact": row[5] if len(row) > 5 else "",
                    "last_thread": row[6] if len(row) > 6 else "",
                    "notes": row[7] if len(row) > 7 else "",
                })
        return contacts
