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
#
# Scope philosophy (Financial Education Mode):
#   ALLOWED: Education about investment concepts, general options by market,
#            risk explanations, wealth-building ladders, compound interest
#   BLOCKED: "Buy X stock", "Put Y% in Z fund", specific product picks,
#            tax filing, legal advice
#
# The line: Saver can EXPLAIN and EDUCATE, but never RECOMMEND a specific
# product or tell you exactly what to buy/sell.

# Hard-blocked: specific product recommendations and regulated advice
HARD_BLOCKED_PATTERNS = [
    # Specific product purchase/sell recommendations
    re.compile(r"\b(buy|sell|short|long)\s+(this|that|the)\s+(stock|share|coin|token|fund)\b", re.IGNORECASE),
    re.compile(r"\b(which|best|top)\s+(stock|share|coin|fund|insurance|loan)\s+(to buy|should I|for me)\b", re.IGNORECASE),
    re.compile(r"\b(recommend|suggest)\s+.{0,20}\s*(specific|particular)\s+(stock|fund|insurance|loan)\b", re.IGNORECASE),
    # Tax filing (not education)
    re.compile(r"\b(file|submit|prepare)\s+(my\s+)?(tax|taxes|tax return)\b", re.IGNORECASE),
    # Legal advice
    re.compile(r"\b(legal advice|sue|lawsuit|lawyer|attorney)\b", re.IGNORECASE),
]

# Investment/finance topics — allowed for EDUCATION, not for specific advice
FINANCE_EDUCATION_TOPICS = re.compile(
    r"\b(invest|stock|shares?|crypto|bitcoin|ethereum|NFT|forex|trading|"
    r"mutual fund|ETF|bond|dividend|gold|savings account|deposit|"
    r"reksa dana|deposito|tabungan|grow my money|build wealth|"
    r"passive income|compound interest|portfolio|diversif|risk|"
    r"money market|SIP|robo.?advisor)\b",
    re.IGNORECASE,
)


def check_scope(text: str) -> tuple[bool, str | None]:
    """Check if the user's message is within Saver's scope.

    Financial Education Mode:
    - BLOCKS specific product recommendations ("buy this stock")
    - ALLOWS investment education ("what is a mutual fund", "should I invest",
      "how to grow my money", "is crypto risky")

    Returns (is_in_scope, reason_if_not).
    """
    # Hard blocks — these are always refused
    for pattern in HARD_BLOCKED_PATTERNS:
        if pattern.search(text):
            return False, "regulated_domain"

    # Everything else is in-scope (including investment education)
    return True, None


# ── Combined guard ─────────────────────────────────────────────────────

def run_input_guard(text: str) -> dict:
    """Run all input guardrails. Returns guard result dict."""
    cleaned, pii_found = redact_pii(text)
    in_scope, reason = check_scope(cleaned)

    # Tag investment education topics so the agent knows to use education mode
    is_finance_education = bool(FINANCE_EDUCATION_TOPICS.search(cleaned))

    return {
        "cleaned_text": cleaned,
        "pii_redacted": pii_found,
        "in_scope": in_scope,
        "scope_reason": reason,
        "finance_education": is_finance_education,
    }
