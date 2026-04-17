"""Input guardrails — PII redaction and scope check."""

from __future__ import annotations

import re

# ── PII patterns ───────────────────────────────────────────────────────

PII_PATTERNS = [
    # Singapore NRIC/FIN: S/T/F/G + 7 digits + letter
    (re.compile(r"\b[STFG]\d{7}[A-Z]\b", re.IGNORECASE), "[NRIC_REDACTED]"),
    # Indonesia KTP: 16 digits
    (re.compile(r"\b\d{16}\b"), "[KTP_REDACTED]"),
    # Phone numbers: various formats
    (re.compile(r"\b(?:\+?65|08)\d{7,10}\b"), "[PHONE_REDACTED]"),
    # Full account numbers: 10+ digits
    (re.compile(r"\b\d{10,16}\b"), "[ACCT_REDACTED]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
]


def redact_pii(text: str) -> tuple[str, bool]:
    """Redact PII from user input. Returns (cleaned_text, was_redacted)."""
    redacted = False
    result = text
    for pattern, replacement in PII_PATTERNS:
        if pattern.search(result):
            result = pattern.sub(replacement, result)
            redacted = True
    return result, redacted


# ── Scope check ────────────────────────────────────────────────────────

OUT_OF_SCOPE_PATTERNS = [
    # Investment advice
    re.compile(r"\b(invest|stock|shares?|crypto|bitcoin|ethereum|NFT|forex|trading|mutual fund|ETF|bond|dividend)\b", re.IGNORECASE),
    # Specific product recommendations
    re.compile(r"\b(which insurance|best insurance|buy insurance|compare insurance|which credit card|best loan)\b", re.IGNORECASE),
    # Tax advice
    re.compile(r"\b(file tax|tax return|tax deduction|tax refund|income tax)\b", re.IGNORECASE),
    # Legal advice
    re.compile(r"\b(legal advice|sue|lawsuit|lawyer|attorney)\b", re.IGNORECASE),
]

# Patterns that override scope check (financial literacy is in-scope)
IN_SCOPE_OVERRIDES = [
    re.compile(r"\b(what is|how does|explain|meaning of|learn about)\b", re.IGNORECASE),
]


def check_scope(text: str) -> tuple[bool, str | None]:
    """Check if the user's message is within Saver's scope.

    Returns (is_in_scope, reason_if_not).
    """
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(text):
            # Check if it's an educational question (in-scope)
            for override in IN_SCOPE_OVERRIDES:
                if override.search(text):
                    return True, None
            return False, "regulated_domain"

    return True, None


# ── Combined guard ─────────────────────────────────────────────────────

def run_input_guard(text: str) -> dict:
    """Run all input guardrails. Returns guard result dict."""
    cleaned, pii_found = redact_pii(text)
    in_scope, reason = check_scope(cleaned)

    return {
        "cleaned_text": cleaned,
        "pii_redacted": pii_found,
        "in_scope": in_scope,
        "scope_reason": reason,
    }
