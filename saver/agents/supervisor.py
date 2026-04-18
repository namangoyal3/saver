"""LangGraph supervisor agent — graph definition, node implementations, orchestration."""

from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from saver.agents.llm_config import detect_provider, get_llm
from saver.agents.prompts import get_scope_refusal, get_system_prompt
from saver.agents.tool_registry import PLANNER_TOOLS, TOOL_FUNCTIONS, TOOL_SCHEMAS, summarize_tool_result
from saver.guardrails.input_guard import run_input_guard
from saver.guardrails.output_guard import run_output_guard
from saver.models import AgentTurnResponse, GuardrailReport, ReasoningStep, UserProfileSnapshot

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility
_detect_provider = detect_provider


# ── LangGraph state ───────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_profile: UserProfileSnapshot
    tool_results: list[dict]
    reasoning_trace: list[dict]
    guardrail_report: dict
    pending_confirmation: dict | None


# ── Graph nodes ───────────────────────────────────────────────────────

def input_guard_node(state: AgentState) -> dict:
    """Run input guardrails on the latest user message."""
    last_msg = state["messages"][-1]
    if not isinstance(last_msg, HumanMessage):
        return {}

    guard_result = run_input_guard(last_msg.content)

    report = state.get("guardrail_report", {})
    report["input_pii_redacted"] = guard_result["pii_redacted"]
    report["input_scope_check"] = "pass" if guard_result["in_scope"] else "blocked"

    if guard_result["pii_redacted"]:
        return {
            "messages": [HumanMessage(content=guard_result["cleaned_text"])],
            "guardrail_report": report,
        }

    return {"guardrail_report": report}


def should_refuse(state: AgentState) -> str:
    """Route: refuse if out of scope, otherwise continue to agent."""
    report = state.get("guardrail_report", {})
    if report.get("input_scope_check") == "blocked":
        return "refuse"
    return "agent"


def refuse_node(state: AgentState) -> dict:
    """Generate a polite refusal for out-of-scope requests."""
    last_msg = state["messages"][-1]
    content = last_msg.content if isinstance(last_msg, HumanMessage) else ""

    topic = "investments and financial products"
    if any(w in content.lower() for w in ("tax", "filing", "deduction")):
        topic = "tax matters"
    elif any(w in content.lower() for w in ("legal", "lawyer", "sue")):
        topic = "legal matters"
    elif any(w in content.lower() for w in ("insurance",)):
        topic = "specific insurance products"

    profile = state["user_profile"]
    refusal = get_scope_refusal(topic, profile.preferred_lang)

    trace = state.get("reasoning_trace", [])
    trace.append({
        "idx": len(trace),
        "agent": "supervisor",
        "action": "refuse",
        "tool_name": None,
        "tool_args_summary": None,
        "result_summary": f"Out of scope: {topic}",
        "latency_ms": 0,
    })

    return {
        "messages": [AIMessage(content=refusal)],
        "reasoning_trace": trace,
    }


def agent_node(state: AgentState) -> dict:
    """Main agent node — calls LLM with tools, handles tool calls."""
    profile = state["user_profile"]
    system_msg = get_system_prompt(profile)
    llm = get_llm()

    msgs = [SystemMessage(content=system_msg)] + state["messages"]

    trace = state.get("reasoning_trace", [])
    tool_results = state.get("tool_results", [])

    # Call LLM with tools
    t0 = time.time()
    try:
        response = llm.invoke(msgs, tools=TOOL_SCHEMAS)
    except Exception as e:
        logger.error("LLM call failed: %s: %s", type(e).__name__, str(e)[:200])
        error_name = type(e).__name__
        user_msgs = {
            "AuthenticationError": "API key is invalid. Please check your configuration.",
            "RateLimitError": "I'm getting too many requests right now. Please wait a moment and try again.",
            "APITimeoutError": "The AI service is taking too long. Please try again.",
            "InternalServerError": "The AI service is experiencing issues. Please try again shortly.",
        }
        error_msg = user_msgs.get(error_name, "I'm having a bit of trouble right now. Could you try asking again?")
        return {
            "messages": [AIMessage(content=error_msg)],
            "reasoning_trace": trace,
        }

    latency = int((time.time() - t0) * 1000)

    if hasattr(response, "tool_calls") and response.tool_calls:
        trace.append({
            "idx": len(trace),
            "agent": "supervisor",
            "action": "plan",
            "tool_name": None,
            "tool_args_summary": f"Planning {len(response.tool_calls)} tool calls",
            "result_summary": None,
            "latency_ms": latency,
        })

        tool_messages = []
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = dict(tc["args"])
            tool_id = tc["id"]

            # Auto-inject user_id
            tool_args["user_id"] = profile.user_id

            t1 = time.time()
            func = TOOL_FUNCTIONS.get(tool_name)
            if func:
                try:
                    valid_params = set(inspect.signature(func).parameters.keys())
                    filtered_args = {k: v for k, v in tool_args.items() if k in valid_params}
                    result = func(**filtered_args)
                except Exception as e:
                    logger.error("Tool %s failed: %s", tool_name, str(e)[:200])
                    result = {"error": str(e)}
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            tool_latency = int((time.time() - t1) * 1000)
            tool_results.append(result)

            specialist = "planner" if tool_name in PLANNER_TOOLS else "analyst"

            trace.append({
                "idx": len(trace),
                "agent": specialist,
                "action": "tool_call",
                "tool_name": tool_name,
                "tool_args_summary": json.dumps({k: v for k, v in tool_args.items() if k != "user_id"}, default=str),
                "result_summary": summarize_tool_result(result),
                "latency_ms": tool_latency,
            })

            tool_messages.append(ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=tool_id,
            ))

        return {
            "messages": [response] + tool_messages,
            "tool_results": tool_results,
            "reasoning_trace": trace,
        }
    else:
        trace.append({
            "idx": len(trace),
            "agent": "supervisor",
            "action": "compose",
            "tool_name": None,
            "tool_args_summary": None,
            "result_summary": f"Final response ({len(response.content)} chars)",
            "latency_ms": latency,
        })

        return {
            "messages": [response],
            "reasoning_trace": trace,
            "tool_results": tool_results,
        }


def should_continue(state: AgentState) -> str:
    """Check if the last message has tool calls or if we're done."""
    last = state["messages"][-1]
    if isinstance(last, ToolMessage):
        return "agent"
    if isinstance(last, AIMessage):
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "agent"
        return "output_guard"
    return "output_guard"


def output_guard_node(state: AgentState) -> dict:
    """Run output guardrails on the agent's response."""
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        return {}

    reply = last.content
    tool_results = state.get("tool_results", [])
    report = state.get("guardrail_report", {})

    guard_result = run_output_guard(reply, tool_results)

    if guard_result["passed"]:
        report["output_grounding_check"] = "pass"
        report["output_scope_check"] = "pass"
    else:
        if not guard_result["grounding_ok"]:
            report["output_grounding_check"] = "violation_cleaned"
        if not guard_result["scope_ok"]:
            report["output_scope_check"] = "blocked"
            reply = "I want to be careful here — let me stick to what I know about your spending and savings. Could you rephrase your question?"
            return {
                "messages": [AIMessage(content=reply)],
                "guardrail_report": report,
            }

    return {"guardrail_report": report}


# ── Build the graph ───────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build the Saver agent LangGraph."""
    graph = StateGraph(AgentState)
    graph.add_node("input_guard", input_guard_node)
    graph.add_node("agent", agent_node)
    graph.add_node("refuse", refuse_node)
    graph.add_node("output_guard", output_guard_node)
    graph.set_entry_point("input_guard")
    graph.add_conditional_edges("input_guard", should_refuse, {"refuse": "refuse", "agent": "agent"})
    graph.add_conditional_edges("agent", should_continue, {"agent": "agent", "output_guard": "output_guard"})
    graph.add_edge("refuse", END)
    graph.add_edge("output_guard", END)
    return graph


def compile_graph():
    """Compile and return the runnable graph."""
    return build_graph().compile()


# ── High-level run function ───────────────────────────────────────────

def run_turn(
    user_message: str,
    profile: UserProfileSnapshot,
    history: list | None = None,
) -> tuple[AgentTurnResponse, list]:
    """Run a single conversation turn through the agent.

    Returns (response, updated_message_history).
    """
    app = compile_graph()

    messages = list(history or [])
    messages.append(HumanMessage(content=user_message))

    initial_state: AgentState = {
        "messages": messages,
        "user_profile": profile,
        "tool_results": [],
        "reasoning_trace": [],
        "guardrail_report": {},
        "pending_confirmation": None,
    }

    result = app.invoke(initial_state)

    # Extract final response
    final_messages = result["messages"]
    reply = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
            reply = msg.content
            break

    if not reply:
        reply = "I'm sorry, I couldn't process that. Could you try rephrasing?"

    trace = result.get("reasoning_trace", [])
    reasoning_steps = [ReasoningStep(**step) for step in trace]

    gr = result.get("guardrail_report", {})
    guardrail_report = GuardrailReport(
        input_pii_redacted=gr.get("input_pii_redacted", False),
        input_scope_check=gr.get("input_scope_check", "pass"),
        output_grounding_check=gr.get("output_grounding_check", "pass"),
        output_scope_check=gr.get("output_scope_check", "pass"),
    )

    return AgentTurnResponse(
        reply=reply,
        reply_language=profile.preferred_lang,
        reasoning_trace=reasoning_steps,
        guardrail_report=guardrail_report,
    ), final_messages
