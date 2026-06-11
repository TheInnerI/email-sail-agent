"""
Email Sail Agent — FareHarbor Booking Service

Integrates with FareHarbor API (v1) for tour/activity booking management.
FareHarbor customers: tour operators, activity providers, charter services.
"""

import httpx
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("email-sail.fareharbor")

FH_API_BASE = "https://api.fareharbor.com/api/external/v1"


class FareHarborService:
    """
    FareHarbor External API v1 wrapper.

    Auth: Bearer token (API key from FareHarbor dashboard)
    Docs: https://developer.fareharbor.com/api/external/v1/

    Requires API access approval from FareHarbor (email support@fareharbor.com).
    """

    def __init__(self, api_key: str, company_shortname: str):
        self.api_key = api_key
        self.shortname = company_shortname
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.shortname)

    async def _get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FH_API_BASE}/companies/{self.shortname}{path}",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, body: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FH_API_BASE}/companies/{self.shortname}{path}",
                headers=self.headers,
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def _delete(self, path: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{FH_API_BASE}/companies/{self.shortname}{path}",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def _put(self, path: str, body: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{FH_API_BASE}/companies/{self.shortname}{path}",
                headers=self.headers,
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Items (tours/activities) ──

    async def get_items(self) -> list[dict]:
        """Get all bookable items/tours."""
        if not self.is_configured:
            return []
        data = await self._get("/items")
        return data.get("items", [])

    async def get_item(self, item_id: int) -> dict:
        """Get a specific item."""
        data = await self._get(f"/items/{item_id}")
        return data.get("item", {})

    # ── Availabilities ──

    async def get_availabilities(
        self,
        item_id: int,
        date: str = None,
    ) -> list[dict]:
        """
        Get available time slots for an item.
        date: YYYY-MM-DD format (optional, defaults to today)
        """
        if not self.is_configured:
            return []
        params = {}
        if date:
            params["date"] = date
        data = await self._get(f"/items/{item_id}/availabilities", params)
        return data.get("availabilities", [])

    # ── Bookings ──

    async def get_bookings(
        self,
        date: str = None,
        status: str = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get bookings, optionally filtered by date or status."""
        if not self.is_configured:
            return []
        params = {"limit": limit}
        if date:
            params["date"] = date
        if status:
            params["status"] = status
        data = await self._get("/bookings", params)
        return data.get("bookings", [])

    async def get_booking(self, booking_id: int) -> dict:
        """Get a specific booking with full details."""
        if not self.is_configured:
            return {}
        data = await self._get(f"/bookings/{booking_id}")
        return data.get("booking", {})

    async def get_bookings_by_create_date(self, date: str) -> list[dict]:
        """Get bookings created on a specific date."""
        if not self.is_configured:
            return []
        data = await self._get("/bookings", {"created": date})
        return data.get("bookings", [])

    async def create_booking(
        self,
        item_id: int,
        customers: list[dict],
        **kwargs,
    ) -> dict:
        """
        Create a new booking.

        customers: [{"name": "John", "email": "john@example.com", "phone": "+1555..."}]
        Optional kwargs: note, pickup_location, custom_fields, etc.
        """
        if not self.is_configured:
            raise ValueError("FareHarbor not configured")
        body = {"item_id": item_id, "customers": customers}
        body.update(kwargs)
        data = await self._post("/bookings", body)
        return data.get("booking", {})

    async def cancel_booking(self, booking_id: int) -> dict:
        """Cancel a booking."""
        if not self.is_configured:
            raise ValueError("FareHarbor not configured")
        return await self._delete(f"/bookings/{booking_id}")

    async def update_booking_note(self, booking_id: int, note: str) -> dict:
        """Update a booking note."""
        if not self.is_configured:
            raise ValueError("FareHarbor not configured")
        return await self._put(f"/bookings/{booking_id}/note", {"note": note})

    async def update_customer_custom_field(
        self, booking_id: int, customer_id: int, field_id: int, value: str
    ) -> dict:
        """Update a customer's custom field value."""
        if not self.is_configured:
            raise ValueError("FareHarbor not configured")
        return await self._put(
            f"/bookings/{booking_id}/customers/{customer_id}/custom-fields/{field_id}",
            {"value": value},
        )

    # ── Customers ──

    async def get_customers(self, limit: int = 50) -> list[dict]:
        """Get customers."""
        if not self.is_configured:
            return []
        data = await self._get("/customers", {"limit": limit})
        return data.get("customers", [])

    async def get_customer(self, customer_id: int) -> dict:
        """Get a specific customer."""
        data = await self._get(f"/customers/{customer_id}")
        return data.get("customer", {})

    # ── Check-ins ──

    async def get_checkins(self, date: str = None) -> list[dict]:
        """Get check-ins."""
        if not self.is_configured:
            return []
        params = {}
        if date:
            params["date"] = date
        data = await self._get("/checkins", params)
        return data.get("checkins", [])

    # ── Helper methods ──

    async def find_booking_by_email(
        self, email: str, date: str = None
    ) -> Optional[dict]:
        """Find a booking by customer email address."""
        bookings = await self.get_bookings(date=date)
        for booking in bookings:
            for customer in booking.get("customers", []):
                if customer.get("email", "").lower() == email.lower():
                    return booking
        return None

    async def find_recent_booking_by_email(
        self, email: str, days: int = 30
    ) -> Optional[dict]:
        """Find the most recent booking by email within N days."""
        if not self.is_configured:
            return None
        from datetime import timedelta
        now = datetime.utcnow()
        for day_offset in range(days):
            date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            booking = await self.find_booking_by_email(email, date=date)
            if booking:
                return booking
        return None

    async def get_today_bookings(self) -> list[dict]:
        """Get today's bookings."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return await self.get_bookings(date=today)

    async def get_upcoming_bookings(self, days: int = 7) -> list[dict]:
        """Get bookings for the next N days."""
        if not self.is_configured:
            return []
        all_bookings = []
        from datetime import timedelta
        now = datetime.utcnow()
        for day in range(days):
            date = (now + timedelta(days=day)).strftime("%Y-%m-%d")
            bookings = await self.get_bookings(date=date)
            all_bookings.extend(bookings)
        return all_bookings

    async def get_no_shows(self, date: str = None) -> list[dict]:
        """Get no-show bookings."""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return await self.get_bookings(date=date, status="no_show")

    async def get_cancelled_bookings(self, date: str = None) -> list[dict]:
        """Get cancelled bookings."""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return await self.get_bookings(date=date, status="cancelled")

    def parse_booking(self, booking: dict) -> dict:
        """Parse a FareHarbor booking into a clean dict."""
        customers = booking.get("customers", [])
        customer = customers[0] if customers else {}
        item = booking.get("item", {})

        return {
            "id": booking.get("pk", ""),
            "booking_id": booking.get("booking_id", ""),
            "item_name": item.get("name", ""),
            "item_id": item.get("pk", ""),
            "customer_name": customer.get("name", ""),
            "customer_email": customer.get("email", ""),
            "customer_phone": customer.get("phone", ""),
            "date": booking.get("start_at", ""),
            "status": booking.get("status", ""),
            "total": booking.get("receipt", {}).get("total", ""),
            "headcount": booking.get("headcount", 0),
            "note": booking.get("note", ""),
            "pickup": booking.get("pickup_location", ""),
        }
