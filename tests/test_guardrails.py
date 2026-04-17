"""Tests for Saver guardrails."""

from saver.guardrails.input_guard import check_scope, redact_pii, run_input_guard
from saver.guardrails.output_guard import check_numeric_grounding, check_output_scope


class TestPIIRedaction:
    def test_nric_redacted(self):
        text, redacted = redact_pii("My NRIC is S1234567A")
        assert redacted
        assert "S1234567A" not in text
        assert "[NRIC_REDACTED]" in text

    def test_phone_redacted(self):
        text, redacted = redact_pii("Call me at +6591234567")
        assert redacted
        assert "91234567" not in text

    def test_clean_text_unchanged(self):
        text, redacted = redact_pii("Where did my money go?")
        assert not redacted
        assert text == "Where did my money go?"


class TestScopeCheck:
    def test_in_scope_spending_question(self):
        ok, _ = check_scope("Where did my money go this week?")
        assert ok

    def test_out_of_scope_crypto(self):
        ok, reason = check_scope("Should I buy Bitcoin?")
        assert not ok
        assert reason == "regulated_domain"

    def test_out_of_scope_tax(self):
        ok, _ = check_scope("Help me file tax return")
        assert not ok

    def test_educational_override(self):
        ok, _ = check_scope("What is an emergency fund?")
        assert ok

    def test_educational_crypto_question(self):
        ok, _ = check_scope("How does crypto work? Explain it to me")
        assert ok


class TestNumericGrounding:
    def test_grounded_numbers(self):
        tool_results = [{"total": 1420000, "currency": "IDR"}]
        ok, ungrounded = check_numeric_grounding("Total: IDR 1,420,000", tool_results)
        assert ok
        assert len(ungrounded) == 0

    def test_ungrounded_number(self):
        tool_results = [{"total": 1420000}]
        ok, ungrounded = check_numeric_grounding("Total: IDR 2,500,000", tool_results)
        assert not ok
        assert 2500000.0 in ungrounded

    def test_small_numbers_exempt(self):
        ok, _ = check_numeric_grounding("3 categories, 7 days", [])
        assert ok


class TestOutputScope:
    def test_clean_output(self):
        ok, _ = check_output_scope("Your fuel spend was 12% higher this week.")
        assert ok

    def test_investment_advice_blocked(self):
        ok, reason = check_output_scope("You should invest in this stock fund.")
        assert not ok
