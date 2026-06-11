"""
Email Sail Agent — Email Classifier Service

Classifies emails into categories using rule-based heuristics + optional LLM.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger("email-sail.classifier")

# Category definitions with keywords and patterns
CATEGORY_RULES = {
    "urgent": {
        "keywords": ["urgent", "asap", "immediately", "emergency", "critical", "today", "right now", "deadline"],
        "patterns": [
            r"need\s+(?:this|it|to|you).*(?:today|asap|now|immediately)",
            r"(?:cancel|reschedule).*(?:today|tomorrow|meeting|appointment)",
            r"respond\s+(?:today|asap|immediately)",
        ],
        "label_color": "#dc2626",  # red
    },
    "customer_inquiry": {
        "keywords": [
            "question", "interested", "pricing", "quote", "cost", "how much",
            "do you", "can you", "are you", "looking for", "need help",
            "inquiry", "information", "details", "services", "offer",
        ],
        "patterns": [
            r"(?:i'?m|we'?re)\s+(?:interested|looking|wanting)",
            r"(?:do|can|could)\s+you\s+(?:help|provide|send|tell)",
            r"(?:how\s+(?:much|long|soon)|what\s+(?:is|are)\s+(?:the|your))",
            r"(?:get\s+in\s+touch|reach\s+out|contact\s+you)",
        ],
        "label_color": "#eab308",  # yellow
    },
    "invoice_payment": {
        "keywords": [
            "invoice", "payment", "paid", "receipt", "billing", "charge",
            "amount due", "balance", "transaction", "paypal", "stripe",
            "gumroad", "purchase", "order", "refund",
        ],
        "patterns": [
            r"(?:invoice|payment|receipt)\s*(?:#|no|number)?\s*\d",
            r"(?:amount|total|due)\s*[\$€£]\s*\d",
            r"(?:thank\s+you\s+for\s+your\s+(?:purchase|order|payment))",
        ],
        "label_color": "#16a34a",  # green
    },
    "newsletter": {
        "keywords": [
            "newsletter", "unsubscribe", "subscription", "digest", "weekly",
            "monthly", "update", "blog", "medium", "substack",
        ],
        "patterns": [
            r"unsubscribe",
            r"view\s+(?:this|the)\s+email\s+in\s+(?:your\s+)?browser",
            r"you(?:'re|\s+are)\s+receiving\s+this",
        ],
        "label_color": "#2563eb",  # blue
    },
    "spam": {
        "keywords": [
            "won", "winner", "lottery", "congratulations", "free money",
            "click here", "act now", "limited time", "no obligation",
            "risk-free", "guarantee", "credit card",
        ],
        "patterns": [
            r"you(?:'ve|\s+have)\s+won",
            r"(?:click|respond)\s+(?:here|now|immediately)",
        ],
        "label_color": "#6b7280",  # gray
    },
    "booking_request": {
        "keywords": [
            "schedule", "book", "appointment", "call meeting", "available",
            "calendar", "zoom", "meet", "consultation", "session",
            "reschedule", "cancel meeting", "set up", "arrange",
        ],
        "patterns": [
            r"(?:can|could|would)\s+we\s+(?:schedule|book|set\s+up|arrange)",
            r"(?:are|is)\s+(?:you|he|she)\s+available",
            r"(?:schedule|book)\s+(?:a|an)\s+(?:call|meeting|session|appointment)",
            r"(?:zoom|google\s+meet|teams)\s+(?:link|call|meeting)",
            r"(?:reschedule|cancel)\s+(?:our\s+)?(?:meeting|appointment|call)",
        ],
        "label_color": "#9333ea",  # purple
    },
    "revenue_alert": {
        "keywords": [
            "abandoned", "cart", "checkout", "incomplete", "failed payment",
            "expired", "renew", "subscription ending", "lapsed",
        ],
        "patterns": [
            r"(?:abandoned|incomplete)\s+(?:cart|checkout|order|payment)",
            r"(?:payment|transaction)\s+(?:failed|declined|error)",
            r"(?:subscription|license|membership)\s+(?:expir|laps|end)",
        ],
        "label_color": "#ea580c",  # orange
    },
    # FareHarbor booking categories
    "fh_booking_change": {
        "keywords": [
            "change", "reschedule", "different time", "move my booking",
            "switch", "modify", "update my booking", "change date",
        ],
        "patterns": [
            r"(?:change|reschedule|move|switch)\s+(?:my\s+)?(?:booking|reservation|tour|appointment)",
            r"(?:different|another)\s+(?:time|date|day)",
            r"(?:can|could)\s+(?:we|I)\s+(?:change|reschedule|move)",
        ],
        "label_color": "#f59e0b",  # amber
    },
    "fh_cancellation": {
        "keywords": [
            "cancel", "can't make it", "won't be able", "can't come",
            "need to cancel", "cancel my", "cancellation",
        ],
        "patterns": [
            r"(?:cancel|cancellation)\s+(?:my\s+)?(?:booking|reservation|tour)",
            r"(?:can't|cannot|won't)\s+(?:make it|come|attend|be there)",
            r"(?:need|want)\s+to\s+cancel",
        ],
        "label_color": "#ef4444",  # red
    },
    "fh_faq": {
        "keywords": [
            "what to bring", "where to meet", "parking", "dress code",
            "what to wear", "how long", "how much", "age limit",
            "what should i", "do i need", "is there", "where is",
            "what time", "how early", "cancel policy", "refund",
        ],
        "patterns": [
            r"(?:what|where|how|when|do|is|are)\s+(?:should|do|does|can|will|is|are)",
            r"(?:what|where|how)\s+(?:to|do|i|we|should)",
            r"(?:parking|meet|bring|wear|dress|arrive|check.in)",
        ],
        "label_color": "#8b5cf6",  # violet
    },
    "fh_group_booking": {
        "keywords": [
            "group", "private", "team building", "corporate", "party",
            "large group", "family reunion", "birthday", "celebration",
            "book for", "reserve for", "block booking",
        ],
        "patterns": [
            r"(?:book|reserve)\s+(?:for|a|an)\s+(?:group|private|team|party|corporate)",
            r"(?:group|private|team)\s+(?:booking|reservation|tour|event)",
            r"(?:how\s+many|number\s+of)\s+(?:people|persons|guests)",
        ],
        "label_color": "#06b6d4",  # cyan
    },
}


def classify_email(subject: str, body: str, from_email: str = "") -> dict:
    """
    Classify an email into a category.
    Returns: {"category": str, "confidence": float, "reason": str}
    """
    text = f"{subject} {body}".lower()
    scores: dict[str, float] = {}

    for category, rules in CATEGORY_RULES.items():
        score = 0.0
        matches = []

        # Keyword matching
        for keyword in rules["keywords"]:
            if keyword in text:
                score += 1.0
                matches.append(f"keyword:{keyword}")

        # Pattern matching (stronger signal)
        for pattern in rules["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += 2.0
                matches.append(f"pattern:{pattern[:30]}")

        # Boost for subject line matches
        subject_lower = subject.lower()
        for keyword in rules["keywords"]:
            if keyword in subject_lower:
                score += 1.5

        if score > 0:
            scores[category] = {
                "score": score,
                "matches": matches[:5],  # Top 5 matches
            }

    if not scores:
        return {"category": "uncategorized", "confidence": 0.0, "reason": "No patterns matched"}

    # Pick highest scoring category
    best = max(scores.items(), key=lambda x: x[1]["score"])
    category = best[0]
    raw_score = best[1]["score"]
    matches = best[1]["matches"]

    # Normalize confidence (sigmoid-ish)
    confidence = min(0.95, raw_score / 8.0)

    return {
        "category": category,
        "confidence": round(confidence, 2),
        "reason": f"Matched: {', '.join(matches[:3])}",
    }


def get_category_label(category: str) -> str:
    """Get the Gmail label name for a category."""
    labels = {
        "urgent": "⛵ Urgent",
        "customer_inquiry": "⛵ Customer Inquiry",
        "invoice_payment": "⛵ Invoice/Payment",
        "newsletter": "⛵ Newsletter",
        "spam": "⛵ Low Priority",
        "booking_request": "⛵ Booking Request",
        "revenue_alert": "⛵ Revenue Alert",
        "fh_booking_change": "🎫 FH: Change",
        "fh_cancellation": "🎫 FH: Cancel",
        "fh_faq": "🎫 FH: FAQ",
        "fh_group_booking": "🎫 FH: Group",
        "uncategorized": "⛵ Uncategorized",
    }
    return labels.get(category, "⛵ Uncategorized")


def get_category_color(category: str) -> str:
    """Get the label color for a category."""
    if category in CATEGORY_RULES:
        return CATEGORY_RULES[category]["label_color"]
    return "#6b7280"
