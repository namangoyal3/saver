"""LangGraph supervisor agent — routes to specialists, composes responses."""

from __future__ import annotations

import inspect
import json
import logging
import os
import time
from typing import Annotated, Any, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from saver.guardrails.input_guard import run_input_guard
from saver.guardrails.output_guard import run_output_guard
from saver.models import (
    ANALYST_INTENTS,
    OUT_OF_SCOPE_INTENTS,
    PLANNER_INTENTS,
    AgentTurnResponse,
    GuardrailReport,
    ReasoningStep,
    UserProfileSnapshot,
)
from saver.tools.forecast import forecast_cashflow, simulate_goal
from saver.tools.goals import create_goal, list_goals, update_goal
from saver.tools.grab_earnings import get_grab_earnings, get_grab_trip_summary
from saver.tools.transactions import (
    get_expense_breakdown,
    get_income_summary,
    get_transactions,
)

load_dotenv()

# ── LLM setup ─────────────────────────────────────────────────────────

PROVIDER_CONFIGS = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "api_key_env": "NVIDIA_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
    },
}


def _detect_provider() -> str:
    """Auto-detect which provider to use based on available API keys."""
    explicit = os.environ.get("LLM_PROVIDER", "").lower()
    if explicit in PROVIDER_CONFIGS:
        return explicit
    # Check for keys in priority order
    for provider in ["nvidia", "groq", "anthropic"]:
        key_env = PROVIDER_CONFIGS[provider]["api_key_env"]
        if os.environ.get(key_env):
            return provider
    return "nvidia"  # default


def get_llm(model: str | None = None) -> ChatOpenAI:
    """Get an LLM instance — auto-detects provider from available API keys."""
    provider = _detect_provider()
    config = PROVIDER_CONFIGS[provider]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or os.environ.get("SUPERVISOR_MODEL", config["default_model"]),
            api_key=os.environ.get(config["api_key_env"], ""),
            temperature=0.3,
            max_tokens=2048,
        )

    return ChatOpenAI(
        model=model or os.environ.get("SUPERVISOR_MODEL", config["default_model"]),
        base_url=config["base_url"],
        api_key=os.environ.get(config["api_key_env"], ""),
        temperature=0.3,
        max_tokens=2048,
    )


# ── Tool registry ─────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "get_expense_breakdown": get_expense_breakdown,
    "get_income_summary": get_income_summary,
    "get_grab_earnings": get_grab_earnings,
    "get_grab_trip_summary": get_grab_trip_summary,
    "forecast_cashflow": forecast_cashflow,
    "simulate_goal": simulate_goal,
    "list_goals": list_goals,
    "create_goal": create_goal,
    "update_goal": update_goal,
}

# LangChain tool schemas for the LLM — user_id is auto-injected, not exposed to LLM
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_expense_breakdown",
            "description": "Get categorized expense breakdown for the current user. Returns total spending and per-category amounts with percentages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {"type": "integer", "description": "Number of days to look back (default 7)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_income_summary",
            "description": "Get income summary with total, weekly average, and source breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {"type": "integer", "description": "Number of days to look back (default 30)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_grab_earnings",
            "description": "Get aggregated Grab platform earnings including gross, net, fees, and incentives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {"type": "integer", "description": "Number of days (default 30)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_grab_trip_summary",
            "description": "Get trip count, hours worked, average earnings per trip, and fuel ratio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {"type": "integer", "description": "Number of days (default 7)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_cashflow",
            "description": "Forecast the user's net cashflow for the next N days based on historical patterns. Returns daily forecast points with confidence bands and risk assessment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "horizon_days": {"type": "integer", "description": "Days to forecast (7-90, default 14)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_goal",
            "description": "Simulate whether a savings goal is feasible given the user's historical cashflow. Returns feasibility assessment, suggested weekly contribution, and risk analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_name": {"type": "string", "description": "Name of the goal"},
                    "target_amount": {"type": "number", "description": "Target savings amount"},
                    "target_months": {"type": "integer", "description": "Months to achieve goal (default 6)"},
                },
                "required": ["goal_name", "target_amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_goals",
            "description": "List all savings goals for the current user.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "Create a new savings goal for the user. Only call this after the user has explicitly confirmed they want to create this goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Goal name"},
                    "target_amount": {"type": "number", "description": "Target amount to save"},
                    "currency": {"type": "string", "description": "Currency code"},
                    "target_date": {"type": "string", "description": "Target date (YYYY-MM-DD)"},
                },
                "required": ["name", "target_amount", "currency"],
            },
        },
    },
]


# ── System prompts ─────────────────────────────────────────────────────

def get_system_prompt(profile: UserProfileSnapshot) -> str:
    lang_instruction = ""
    if profile.preferred_lang == "id":
        lang_instruction = "Reply in Bahasa Indonesia. Use simple, warm, informal language."
    else:
        lang_instruction = "Reply in English. Use simple, warm, non-judgmental language."

    return f"""You are Saver, a financial wellness coach for Grab driver-partners and delivery-partners in Southeast Asia. You help partners understand their money, plan savings, and build financial resilience.

CURRENT USER: {profile.name} ({profile.market.value} market, {profile.partner_types[0].value} partner, earnings tier: {profile.earnings_tier.value})
CURRENCY: {profile.currency}
LANGUAGE: {lang_instruction}

CRITICAL RULES:
1. NEVER generate or guess financial numbers. Every monetary figure in your response MUST come from a tool call result. If you don't have data, say so.
2. You are NOT a licensed financial advisor. NEVER recommend specific investments, insurance products, stocks, crypto, or specific loan products.
3. If the user asks about investments, insurance products, stocks, crypto, tax filing, or legal matters — politely decline and explain that you focus on budgeting and savings. Suggest they speak to a licensed financial advisor.
4. NEVER moralize or judge the user's spending. Be warm, supportive, and non-judgmental.
5. For any action that changes the user's goals or money (creating a goal, setting up autosave), ALWAYS ask for explicit confirmation first.
6. Keep responses concise — under 150 words for simple queries, under 250 for complex analysis.

WHAT YOU CAN DO:
- Analyze spending patterns and explain where money is going
- Summarize income and earnings from Grab
- Forecast cashflow for the coming weeks
- Help set and track savings goals
- Answer general financial literacy questions (what is an emergency fund, how budgeting works, etc.)
- Provide behavioral nudges for better money management

HOW TO RESPOND:
1. First, call the relevant tools to get actual data
2. Analyze the data from tool results
3. Explain findings in simple language using ONLY numbers from the tools
4. If relevant, suggest one concrete, actionable next step
5. If the user wants to create a goal, first simulate it, then ask for confirmation before creating"""


SCOPE_REFUSAL = """I appreciate you asking, but that's outside what I can help with. I focus on budgeting, savings, and understanding your earnings — I'm not licensed to give advice on {topic}.

For that kind of guidance, I'd recommend speaking with a licensed financial advisor. Would you like me to help with your savings or spending instead?"""


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

    # If PII was redacted, replace the message
    if guard_result["pii_redacted"]:
        return {
            "messages": [HumanMessage(content=guard_result["cleaned_text"])],
            "guardrail_report": report,
        }

    if not guard_result["in_scope"]:
        return {"guardrail_report": report}

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

    # Detect topic for personalized refusal
    topic = "investments and financial products"
    if any(w in content.lower() for w in ("tax", "filing", "deduction")):
        topic = "tax matters"
    elif any(w in content.lower() for w in ("legal", "lawyer", "sue")):
        topic = "legal matters"
    elif any(w in content.lower() for w in ("insurance",)):
        topic = "specific insurance products"

    profile = state["user_profile"]
    refusal = SCOPE_REFUSAL.format(topic=topic)
    if profile.preferred_lang == "id":
        refusal = f"Terima kasih sudah bertanya, tapi itu di luar kemampuan saya. Saya fokus membantu soal anggaran dan tabungan — saya tidak punya lisensi untuk memberikan saran soal {topic}.\n\nUntuk itu, saya sarankan bicara dengan penasihat keuangan berlisensi. Mau saya bantu soal tabungan atau pengeluaranmu?"

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

    # Build messages for LLM
    msgs = [SystemMessage(content=system_msg)] + state["messages"]

    trace = state.get("reasoning_trace", [])
    tool_results = state.get("tool_results", [])

    # Call LLM with tools
    t0 = time.time()
    try:
        response = llm.invoke(msgs, tools=TOOL_SCHEMAS)
    except Exception as e:
        logging.getLogger(__name__).error("LLM call failed: %s: %s", type(e).__name__, str(e)[:200])

        # Map to user-friendly messages
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

    # Check if the LLM wants to call tools
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

        # Execute tool calls
        tool_messages = []
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = dict(tc["args"])  # copy to avoid mutating
            tool_id = tc["id"]

            # Auto-inject user_id — LLM doesn't need to know internal IDs
            tool_args["user_id"] = profile.user_id

            t1 = time.time()
            func = TOOL_FUNCTIONS.get(tool_name)
            if func:
                try:
                    # Filter args to only valid params for this function
                    valid_params = set(inspect.signature(func).parameters.keys())
                    filtered_args = {k: v for k, v in tool_args.items() if k in valid_params}
                    result = func(**filtered_args)
                except Exception as e:
                    logging.getLogger(__name__).error("Tool %s failed: %s", tool_name, str(e)[:200])
                    result = {"error": str(e)}
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            tool_latency = int((time.time() - t1) * 1000)
            tool_results.append(result)

            # Determine specialist from tool name
            specialist = "analyst"
            if tool_name in ("forecast_cashflow", "simulate_goal", "list_goals", "create_goal"):
                specialist = "planner"

            trace.append({
                "idx": len(trace),
                "agent": specialist,
                "action": "tool_call",
                "tool_name": tool_name,
                "tool_args_summary": json.dumps({k: v for k, v in tool_args.items() if k != "user_id"}, default=str),
                "result_summary": _summarize_result(result),
                "latency_ms": tool_latency,
            })

            tool_messages.append(ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=tool_id,
            ))

        # Return tool results to trigger another LLM call
        return {
            "messages": [response] + tool_messages,
            "tool_results": tool_results,
            "reasoning_trace": trace,
        }
    else:
        # LLM produced a final response (no tool calls)
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
    """Check if the last message has tool calls that need executing, or if we're done."""
    last = state["messages"][-1]
    # If the last message is a ToolMessage, we need another LLM call
    if isinstance(last, ToolMessage):
        return "agent"
    # If AI message with no tool calls, we're done
    if isinstance(last, AIMessage):
        if hasattr(last, "tool_calls") and last.tool_calls:
            # This shouldn't happen since we handle tool calls in agent_node,
            # but just in case
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
            # Log the ungrounded numbers but don't block (for prototype)
        if not guard_result["scope_ok"]:
            report["output_scope_check"] = "blocked"
            # Replace with safe message
            reply = "I want to be careful here — let me stick to what I know about your spending and savings. Could you rephrase your question?"
            return {
                "messages": [AIMessage(content=reply)],
                "guardrail_report": report,
            }

    return {"guardrail_report": report}


def _summarize_result(result: dict) -> str:
    """Create a short summary of a tool result for the trace."""
    if "error" in result:
        return f"Error: {result['error']}"
    if "total" in result:
        return f"total={result['total']} {result.get('currency', '')}"
    if "gross_earnings" in result:
        return f"gross={result['gross_earnings']} {result.get('currency', '')}"
    if "total_trips" in result:
        return f"trips={result['total_trips']}, hours={result.get('total_hours', '?')}"
    if "feasible" in result:
        return f"feasible={result['feasible']}, suggested={result.get('suggested_weekly_contribution', '?')}"
    if "goal_id" in result:
        return f"goal {result.get('status', 'unknown')}: {result.get('name', '')}"
    if isinstance(result, list):
        return f"{len(result)} items"
    if "points" in result:
        s = result.get("summary", {})
        return f"forecast: min_balance={s.get('expected_min_balance', '?')}, neg_prob={s.get('probability_negative_balance', '?')}"
    return str(result)[:100]


# ── Build the graph ───────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build the Saver agent LangGraph."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input_guard", input_guard_node)
    graph.add_node("agent", agent_node)
    graph.add_node("refuse", refuse_node)
    graph.add_node("output_guard", output_guard_node)

    # Set entry point
    graph.set_entry_point("input_guard")

    # Add edges
    graph.add_conditional_edges("input_guard", should_refuse, {"refuse": "refuse", "agent": "agent"})
    graph.add_conditional_edges("agent", should_continue, {"agent": "agent", "output_guard": "output_guard"})
    graph.add_edge("refuse", END)
    graph.add_edge("output_guard", END)

    return graph


def compile_graph():
    """Compile and return the runnable graph."""
    graph = build_graph()
    return graph.compile()


# ── High-level run function ───────────────────────────────────────────

def run_turn(
    user_message: str,
    profile: UserProfileSnapshot,
    history: list | None = None,
) -> AgentTurnResponse:
    """Run a single conversation turn through the agent."""
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

    t0 = time.time()
    result = app.invoke(initial_state)
    total_ms = int((time.time() - t0) * 1000)

    # Extract final response
    final_messages = result["messages"]
    reply = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
            reply = msg.content
            break

    if not reply:
        reply = "I'm sorry, I couldn't process that. Could you try rephrasing?"

    # Build trace
    trace = result.get("reasoning_trace", [])
    reasoning_steps = [ReasoningStep(**step) for step in trace]

    # Build guardrail report
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
