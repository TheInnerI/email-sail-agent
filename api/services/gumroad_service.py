"""
Email Sail Agent — Gumroad Revenue Service
"""

import logging
from typing import Optional
from datetime import datetime

import httpx

from api.config import settings

logger = logging.getLogger("email-sail.gumroad")

GUMROAD_API_BASE = "https://api.gumroad.com/v2"


class GumroadService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GUMROAD_API_KEY

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: dict = None) -> dict:
        if not self.is_configured:
            raise ValueError("Gumroad API key not configured")

        if params is None:
            params = {}
        params["access_token"] = self.api_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GUMROAD_API_BASE}{path}", params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()

    async def list_products(self) -> list[dict]:
        """List all Gumroad products."""
        data = await self._get("/products")
        return data.get("products", [])

    async def get_sales(self, product_id: str = None, limit: int = 50) -> list[dict]:
        """Get recent sales."""
        params = {"limit": limit}
        if product_id:
            params["product_id"] = product_id
        data = await self._get("/sales", params)
        return data.get("sales", [])

    async def detect_abandoned_carts(self) -> list[dict]:
        """
        Detect potential abandoned carts.
        Gumroad doesn't have a direct abandoned cart API, so we look for:
        - Failed payments
        - Refunded sales
        - Sales with specific patterns
        """
        if not self.is_configured:
            return []

        sales = await self.get_sales(limit=100)
        alerts = []

        for sale in sales:
            # Failed payment
            if sale.get("status") == "failed":
                alerts.append({
                    "type": "failed_payment",
                    "product_id": sale.get("product_id", ""),
                    "product_name": sale.get("product_name", ""),
                    "customer_email": sale.get("email", ""),
                    "amount": sale.get("price", 0),
                    "sale_id": sale.get("id", ""),
                    "detected_at": datetime.now().isoformat(),
                })

            # Refunded
            if sale.get("status") == "refunded":
                alerts.append({
                    "type": "refunded",
                    "product_id": sale.get("product_id", ""),
                    "product_name": sale.get("product_name", ""),
                    "customer_email": sale.get("email", ""),
                    "amount": sale.get("price", 0),
                    "sale_id": sale.get("id", ""),
                    "detected_at": datetime.now().isoformat(),
                })

        return alerts

    async def get_revenue_summary(self) -> dict:
        """Get a summary of recent revenue."""
        if not self.is_configured:
            return {"configured": False}

        sales = await self.get_sales(limit=100)
        total = sum(s.get("price", 0) for s in sales if s.get("status") == "paid")
        failed = sum(1 for s in sales if s.get("status") == "failed")
        refunded = sum(1 for s in sales if s.get("status") == "refunded")

        return {
            "configured": True,
            "total_revenue": total,
            "total_sales": len([s for s in sales if s.get("status") == "paid"]),
            "failed_payments": failed,
            "refunded": refunded,
            "at_risk": failed * 49,  # Estimate: avg cart $49
        }
