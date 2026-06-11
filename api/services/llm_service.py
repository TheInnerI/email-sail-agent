"""
Email Sail Agent — OpenRouter LLM Service

Unified LLM router via OpenRouter API.
Supports: Claude, GPT-4o, Kimi, Hermes, and 100+ models.
Docs: https://openrouter.ai/docs
Pricing: https://openrouter.ai/models
"""

import logging
import httpx
from typing import Optional
from api.config import settings

logger = logging.getLogger("email-sail.llm")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://email-sail.innerinetcompany.com",
    "X-Title": "Email Sail Agent",
}

# Model presets — map tier to OpenRouter model ID
# All models verified to exist on OpenRouter as of 2026-06-11
MODELS = {
    # Free tier
    "free": "openrouter/owl-alpha",
    "free_2": "meta-llama/llama-3.1-8b-instruct:free",
    # Cheap tier (good enough for drafts)
    "cheap": "openrouter/owl-alpha",
    "cheap_2": "openrouter/auto",
    "cheap_3": "mistralai/mistral-7b-instruct:free",
    # Standard tier (quality drafts)
    "standard": "openai/gpt-4o-mini",
    "standard_2": "anthropic/claude-sonnet-4",
    # Premium tier (best quality)
    "premium": "anthropic/claude-sonnet-4",
    "premium_2": "openai/gpt-4o",
}

# Default model per user tier
TIER_MODEL_MAP = {
    "free": "free",
    "starter": "cheap",
    "pro": "standard",
    "full": "premium",
}


class OpenRouterError(Exception):
    """OpenRouter API error."""
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class LLMService:
    """
    Unified LLM service via OpenRouter.

    Usage:
        llm = LLMService(api_key="sk-or-...")
        response = await llm.chat(prompt="Write an email response", tier="cheap")
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        headers.update(OPENROUTER_HEADERS)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_model(self, tier: str = "cheap", preferred_model: str = None) -> str:
        """Get the OpenRouter model ID for a tier."""
        if preferred_model:
            # Allow direct model override (e.g., "anthropic/claude-sonnet-4")
            if "/" in preferred_model:
                return preferred_model
            # Allow named presets
            if preferred_model in MODELS:
                return MODELS[preferred_model]
        return MODELS.get(TIER_MODEL_MAP.get(tier, "cheap"), MODELS["cheap"])

    async def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        tier: str = "cheap",
        model: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        messages: list[dict] = None,
    ) -> dict:
        """
        Send a chat completion request to OpenRouter.

        Args:
            prompt: User message / prompt
            system_prompt: System message (optional)
            tier: free / cheap / standard / premium
            model: Override model (e.g., "anthropic/claude-sonnet-4")
            max_tokens: Max response tokens
            temperature: 0.0-2.0
            messages: Full conversation history (optional, overrides prompt)

        Returns:
            dict with: text, model, usage, raw_response

        Raises:
            OpenRouterError: On API failure
        """
        if not self.is_configured:
            raise OpenRouterError(
                "OpenRouter API key not configured. "
                "Set OPENROUTER_API_KEY in .env"
            )

        model_id = self.get_model(tier, model)

        # Build messages
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        client = self._get_client()

        try:
            resp = await client.post(
                OPENROUTER_API_URL,
                headers=self._get_headers(),
                json=payload,
            )

            if resp.status_code != 200:
                body = resp.text
                logger.error(
                    "OpenRouter error %s: %s", resp.status_code, body[:500]
                )
                raise OpenRouterError(
                    f"OpenRouter returned {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=body,
                )

            data = resp.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]

            return {
                "text": text,
                "model": data.get("model", model_id),
                "usage": data.get("usage", {}),
                "raw_response": data,
            }

        except httpx.TimeoutException:
            raise OpenRouterError("OpenRouter request timed out after 60s")
        except (KeyError, IndexError) as e:
            raise OpenRouterError(f"Unexpected response format: {e}")

    async def draft_email_response(
        self,
        subject: str,
        sender_name: str,
        sender_email: str,
        email_body: str,
        category: str,
        tone: str = "professional",
        business_info: str = "",
        tier: str = "cheap",
        preferred_model: str = None,
        max_words: int = 200,
        user_name: str = "",
    ) -> dict:
        """
        Specialized method: draft an email response.

        Returns dict with: text, model, usage
        """
        system_prompt = self._build_email_system_prompt(tone, business_info, user_name)
        user_prompt = self._build_email_user_prompt(
            subject, sender_name, sender_email, email_body, category
        )

        word_limit = max_words

        full_prompt = f"""{user_prompt}

Write a response in under {word_limit} words. HTML format. No placeholders like [Your Name] — write as the business owner."""

        return await self.chat(
            prompt=full_prompt,
            system_prompt=system_prompt,
            tier=tier,
            model=preferred_model,
            max_tokens=min(1000, int(word_limit * 2.5)),  # rough token estimate
            temperature=0.7,
        )

    @staticmethod
    def _build_email_system_prompt(tone: str, business_info: str, user_name: str = "") -> str:
        tone_guides = {
            "professional": (
                "You write in a professional, clear, and courteous tone. "
                "Be direct but warm. Never robotic."
            ),
            "warm": (
                "You write in a warm, friendly, and personal tone. "
                "Show genuine care. Use the person's name. Be human."
            ),
            "direct": (
                "You write in a concise, direct tone. "
                "Get to the point quickly. No fluff. Respect their time."
            ),
            "empathetic": (
                "You write in an empathetic, understanding tone. "
                "Acknowledge their situation first. Show you care."
            ),
        }

        base = tone_guides.get(tone, tone_guides["professional"])

        parts = [base]

        if business_info:
            parts.append(f"\nBusiness context:\n{business_info}")

        parts.append(
            "\nRules:\n"
            "- Write as the business owner (first person)\n"
            "- Use the sender's name in the greeting\n"
            "- Address their specific question/request directly\n"
            "- Include a clear next step or call to action\n"
            f"- Sign off as: {user_name}\n"
            "- HTML format (use <p>, <br>, <strong> as needed)\n"
            "- No placeholders — write a complete, ready-to-send response"
        )

        # Add custom signature if provided
        if user_name:
            parts.append(f"\n\nSignature to use at the end of the email:\n{user_name}")

        return "\n".join(parts)

    @staticmethod
    def _build_email_user_prompt(
        subject: str,
        sender_name: str,
        sender_email: str,
        email_body: str,
        category: str,
    ) -> str:
        category_context = {
            "customer_inquiry": "This is a customer inquiry about services or pricing. Be helpful and include a clear next step.",
            "booking_request": "This is a scheduling request. Propose specific times and make it easy to book.",
            "invoice_payment": "This is billing/payment related. Be clear about amounts, due dates, and methods.",
            "urgent": "This is urgent. Acknowledge the urgency and provide a clear, immediate response.",
            "revenue_alert": "This is a revenue recovery situation. Be empathetic, not pushy. Offer help.",
            "fh_booking_change": "The customer wants to change an existing booking. Be helpful and check availability.",
            "fh_cancellation": "The customer wants to cancel. Be empathetic. Explain policy clearly.",
            "fh_faq": "The customer has a question about your service. Answer clearly and helpfully.",
            "fh_group_booking": "The customer is inquiring about a group booking. Provide options and pricing.",
        }.get(category, "Respond helpfully and professionally to this email.")

        return f"""Write a response to this email:

From: {sender_name} <{sender_email}>
Subject: {subject}

{email_body[:3000]}

Context: {category_context}"""


# ── Singleton ──────────────────────────────────────────────────

_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
