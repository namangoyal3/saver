"""Integration tests for agent guardrails and tool routing (no LLM calls)."""

from saver.agents.supervisor import (
    AgentState,
    input_guard_node,
    output_guard_node,
    refuse_node,
    should_refuse,
)
from saver.models import UserProfileSnapshot
from langchain_core.messages import AIMessage, HumanMessage


def _make_state(message: str, user_id: str = "budi-001") -> AgentState:
    profile = UserProfileSnapshot(
        user_id=user_id, name="Budi", market="ID", preferred_lang="en",
        partner_types=["delivery"], earnings_tier="L",
        financial_persona="firefighter", currency="IDR",
    )
    return {
        "messages": [HumanMessage(content=message)],
        "user_profile": profile,
        "tool_results": [],
        "reasoning_trace": [],
        "guardrail_report": {},
        "pending_confirmation": None,
    }


class TestInputGuardNode:
    def test_clean_input_passes(self):
        state = _make_state("Where did my money go?")
        result = input_guard_node(state)
        report = result.get("guardrail_report", state["guardrail_report"])
        assert report.get("input_scope_check") == "pass"

    def test_pii_is_redacted(self):
        state = _make_state("My NRIC is S1234567A")
        result = input_guard_node(state)
        assert result["guardrail_report"]["input_pii_redacted"] is True
        # Check the message was replaced
        assert "NRIC_REDACTED" in result["messages"][0].content

    def test_out_of_scope_flagged(self):
        state = _make_state("Should I buy Bitcoin?")
        result = input_guard_node(state)
        assert result["guardrail_report"]["input_scope_check"] == "blocked"


class TestRouting:
    def test_in_scope_routes_to_agent(self):
        state = _make_state("Where did my money go?")
        state["guardrail_report"] = {"input_scope_check": "pass"}
        assert should_refuse(state) == "agent"

    def test_out_of_scope_routes_to_refuse(self):
        state = _make_state("Buy Bitcoin")
        state["guardrail_report"] = {"input_scope_check": "blocked"}
        assert should_refuse(state) == "refuse"


class TestRefuseNode:
    def test_refusal_is_polite(self):
        state = _make_state("Should I invest in stocks?")
        result = refuse_node(state)
        reply = result["messages"][0].content
        assert "licensed" in reply.lower() or "outside" in reply.lower()
        assert "advisor" in reply.lower() or "penasihat" in reply.lower()

    def test_refusal_detects_tax_topic(self):
        state = _make_state("Help me file tax return")
        result = refuse_node(state)
        reply = result["messages"][0].content
        assert "tax" in reply.lower()


class TestOutputGuardNode:
    def test_clean_output_passes(self):
        state = _make_state("test")
        state["messages"] = [AIMessage(content="Your spending was IDR 718,984.")]
        state["tool_results"] = [{"total": 718984.39, "currency": "IDR"}]
        result = output_guard_node(state)
        report = result.get("guardrail_report", {})
        assert report.get("output_grounding_check", "pass") == "pass"
