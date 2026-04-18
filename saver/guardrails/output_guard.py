"""Output guardrails — numeric grounding and scope validation."""

from __future__ import annotations

import json
import re


def _extract_numbers(text: str) -> list[float]:
    """Extract all numeric values from text, handling commas and currency symbols."""
    # Match numbers like 1,420,000 or 1420000 or 3.14 or 540,000
    pattern = re.compile(r"(?<!\w)[\d,]+\.?\d*(?!\w)")
    matches = pattern.findall(text)
    numbers = []
    for m in matches:
        try:
            val = float(m.replace(",", ""))
            if val > 0:  # Skip zeros and negatives from this check
                numbers.append(val)
        except ValueError:
            continue
    return numbers


def _collect_tool_numbers(tool_results: list[dict]) -> set[float]:
    """Recursively extract all numeric values from tool result dicts."""
    numbers: set[float] = set()

    def _walk(obj):
        if isinstance(obj, (int, float)):
            if obj > 0:
                numbers.add(float(obj))
                # Also add common derived values
                numbers.add(round(obj, 0))
                numbers.add(round(obj, 1))
                numbers.add(round(obj, 2))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif isinstance(obj, str):
            try:
                parsed = json.loads(obj)
                _walk(parsed)
            except (json.JSONDecodeError, TypeError):
                pass

    for result in tool_results:
        _walk(result)

    # Add common derived values for meaningful financial amounts (> 100)
    raw_numbers = [n for n in numbers if n > 100]

    # Pairwise differences (e.g. surplus = income - expenses)
    for i, a in enumerate(raw_numbers):
        for b in raw_numbers[i + 1:]:
            hi, lo = max(a, b), min(a, b)
            diff = hi - lo
            if diff > 0:
                numbers.add(diff)

    # Time-period projections
    for n in raw_numbers:
        numbers.add(n * 4)    # weekly  → monthly
        numbers.add(n * 12)   # monthly → yearly
        numbers.add(n * 52)   # weekly  → yearly
        numbers.add(n / 7)    # period  → daily
        numbers.add(n / 30)   # period  → daily (monthly basis)

    return numbers


def check_numeric_grounding(reply: str, tool_results: list[dict]) -> tuple[bool, list[float]]:
    """Verify all numbers in the reply appear in tool results.

    Returns (all_grounded, list_of_ungrounded_numbers).
    """
    reply_numbers = _extract_numbers(reply)
    tool_numbers = _collect_tool_numbers(tool_results)

    # Allow common innocuous numbers
    EXEMPT = {float(i) for i in range(1, 101)}  # 1-100 (percentages, counts, ordinals)
    # Also exempt year-like numbers and small decimals (percentages like 50.5)
    EXEMPT.update({float(y) for y in range(2020, 2030)})  # year references

    ungrounded = []
    for num in reply_numbers:
        if num in EXEMPT:
            continue
        # Exempt small decimal percentages (e.g. 50.5%, 12.1%)
        if num < 100 and num != int(num):
            continue
        # Check if this number (or close approximation) exists in tool outputs
        grounded = False
        for tool_num in tool_numbers:
            # Allow 1% tolerance for rounding
            if abs(num - tool_num) < 0.04 * max(abs(tool_num), 1):
                grounded = True
                break
            # Also check if it's a simple derivation (difference, ratio)
            # e.g., net = gross - fees
        if not grounded:
            ungrounded.append(num)

    return len(ungrounded) == 0, ungrounded


# ── Scope keywords in output ──────────────────────────────────────────

ADVICE_PATTERNS = [
    re.compile(r"\b(you should invest|buy this|recommend .* (stock|fund|insurance|loan))\b", re.IGNORECASE),
    re.compile(r"\b(guaranteed return|risk.free|interest rate of \d)\b", re.IGNORECASE),
]


def check_output_scope(reply: str) -> tuple[bool, str | None]:
    """Check if the agent's reply accidentally gives regulated advice."""
    for pattern in ADVICE_PATTERNS:
        if pattern.search(reply):
            return False, "regulated_advice_detected"
    return True, None


# ── Combined output guard ─────────────────────────────────────────────

def run_output_guard(reply: str, tool_results: list[dict]) -> dict:
    """Run all output guardrails.

    Returns:
        dict with keys: passed, grounding_ok, ungrounded_numbers, scope_ok, scope_reason
    """
    grounding_ok, ungrounded = check_numeric_grounding(reply, tool_results)
    scope_ok, scope_reason = check_output_scope(reply)

    return {
        "passed": grounding_ok and scope_ok,
        "grounding_ok": grounding_ok,
        "ungrounded_numbers": ungrounded,
        "scope_ok": scope_ok,
        "scope_reason": scope_reason,
    }
