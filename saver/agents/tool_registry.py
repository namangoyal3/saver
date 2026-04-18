"""Tool registry — maps tool names to functions and LLM-facing schemas."""

from __future__ import annotations

from saver.tools.actionable import get_daily_target, get_earnings_efficiency, get_smart_savings_plan, get_upcoming_bills
from saver.tools.forecast import forecast_cashflow, simulate_goal
from saver.tools.goals import create_goal, list_goals, update_goal
from saver.tools.grab_earnings import get_grab_earnings, get_grab_trip_summary
from saver.tools.transactions import get_expense_breakdown, get_income_summary, get_transactions

# Python function registry — user_id is auto-injected by the agent node
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
    "get_daily_target": get_daily_target,
    "get_earnings_efficiency": get_earnings_efficiency,
    "get_upcoming_bills": get_upcoming_bills,
    "get_smart_savings_plan": get_smart_savings_plan,
}

# Specialist routing: which agent handles which tools
PLANNER_TOOLS = frozenset({
    "forecast_cashflow", "simulate_goal", "list_goals", "create_goal", "update_goal",
    "get_daily_target", "get_upcoming_bills", "get_smart_savings_plan", "get_earnings_efficiency",
})

# LLM-facing tool schemas — user_id is NOT exposed (auto-injected)
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
    {
        "type": "function",
        "function": {
            "name": "get_daily_target",
            "description": "Get today's earnings target — how much the user needs to earn today to stay on track with their weekly expenses and savings goals. Returns daily target, amount earned so far, and how much more is needed.",
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
            "name": "get_earnings_efficiency",
            "description": "Analyze earnings efficiency — earnings per hour, earnings per trip, fuel cost per trip, food cost per trip, and profit per trip. Includes optimization suggestions like 'pack lunch to save X/week'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {"type": "integer", "description": "Days to analyze (default 7)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_bills",
            "description": "Show upcoming bills and obligations predicted from historical patterns. Shows days until due, amount needed, and whether the user has enough to cover them.",
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
            "name": "get_smart_savings_plan",
            "description": "Generate a smart auto-save plan based on earnings patterns. Creates rules like 'On good days (earn above X), auto-save Y. On tough days, skip.' Shows projected monthly and yearly savings.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def summarize_tool_result(result: dict) -> str:
    """Create a short summary of a tool result for the trace."""
    if "error" in result:
        return f"Error: {result['error']}"
    if "daily_target" in result:
        return f"target={result['daily_target']}, needed={result.get('still_needed_today', '?')} {result.get('currency', '')}"
    if "earnings_per_hour" in result:
        return f"per_hr={result['earnings_per_hour']}, per_trip={result.get('earnings_per_trip', '?')} {result.get('currency', '')}"
    if "bills" in result:
        return f"{len(result['bills'])} bills, shortfall={result.get('shortfall', 0)} {result.get('currency', '')}"
    if "has_plan" in result:
        return f"plan={'yes' if result['has_plan'] else 'no'}, monthly={result.get('projected_monthly_savings', '?')} {result.get('currency', '')}"
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
