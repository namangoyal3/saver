"""FastAPI web application for Saver dashboard."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from saver.agents.supervisor import run_turn
from saver.data.db import get_conn, init_db
from saver.data.seed import seed_all
from saver.models import UserProfileSnapshot
from saver.tools.forecast import forecast_cashflow, simulate_goal
from saver.tools.goals import create_goal, list_goals
from saver.tools.grab_earnings import get_grab_earnings, get_grab_trip_summary
from saver.tools.transactions import get_expense_breakdown, get_income_summary

load_dotenv()

import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
app = FastAPI(title="Saver — Financial Wellness Coach")

_session_secret = os.environ.get("SESSION_SECRET")
if not _session_secret:
    _session_secret = "saver-dev-secret-change-in-prod"
    logger.warning("SESSION_SECRET not set — using insecure default. Set SESSION_SECRET env var in production.")
app.add_middleware(SessionMiddleware, secret_key=_session_secret)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Ensure DB is seeded
init_db()


def _get_profile(user_id: str) -> UserProfileSnapshot | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    return UserProfileSnapshot(
        user_id=row["user_id"], name=row["name"], market=row["market"],
        preferred_lang=row["preferred_lang"], partner_types=[row["partner_types"]],
        earnings_tier=row["earnings_tier"], financial_persona=row["financial_persona"],
        currency=row["currency"],
    )


# ── Routes ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=302)
    with get_conn() as conn:
        users = conn.execute("SELECT user_id, name, market, currency FROM users").fetchall()
    return templates.TemplateResponse(request, "login.html", {"users": [dict(u) for u in users]})


@app.post("/login")
async def login(request: Request, user_id: str = Form(...)):
    profile = _get_profile(user_id)
    if not profile:
        return RedirectResponse("/", status_code=302)
    request.session["user_id"] = user_id
    request.session["user_name"] = profile.name
    request.session["chat_history"] = []
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)

    profile = _get_profile(user_id)

    # Fetch dashboard data — current + previous period for deltas
    expenses = get_expense_breakdown(user_id, 7)
    expenses_prev = get_expense_breakdown(user_id, 14)  # 14d for comparison
    income = get_income_summary(user_id, 30)
    income_prev = get_income_summary(user_id, 60)
    grab = get_grab_earnings(user_id, 30)
    trips = get_grab_trip_summary(user_id, 7)
    trips_prev = get_grab_trip_summary(user_id, 14)
    forecast = forecast_cashflow(user_id, 14)
    goals = list_goals(user_id)

    # Compute week-over-week deltas
    def _delta(current, previous_total, divisor=2):
        prev_avg = previous_total / divisor if divisor else 0
        if prev_avg == 0:
            return 0
        return round((current - prev_avg) / prev_avg * 100, 1)

    deltas = {
        "expenses": _delta(expenses["total"], expenses_prev["total"]),
        "income": _delta(income["total_income"], income_prev["total_income"]),
        "grab_net": _delta(grab["net_earnings"], grab["net_earnings"], 1),  # no prev available simply
        "trips": _delta(trips["total_trips"], trips_prev["total_trips"]),
    }

    return templates.TemplateResponse(request, "dashboard.html", {
        "profile": profile,
        "expenses": expenses,
        "income": income,
        "grab": grab,
        "trips": trips,
        "forecast": forecast,
        "goals": goals,
        "deltas": deltas,
    })


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)
    profile = _get_profile(user_id)
    messages = request.session.get("chat_messages", [])
    return templates.TemplateResponse(request, "chat.html", {
        "profile": profile,
        "messages": messages,
    })


@app.post("/chat/send")
async def chat_send(request: Request, message: str = Form(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    # Input validation
    message = message.strip()
    if not message:
        return JSONResponse({"reply": "Please type a message.", "trace": [], "guardrails": {}})
    if len(message) > 2000:
        return JSONResponse({"reply": "Message too long — please keep it under 2000 characters.", "trace": [], "guardrails": {}})

    profile = _get_profile(user_id)
    if not profile:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # Get chat history from session
    chat_messages = request.session.get("chat_messages", [])

    # Build LangChain history from session
    from langchain_core.messages import AIMessage, HumanMessage
    history = []
    for msg in chat_messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        else:
            history.append(AIMessage(content=msg["content"]))

    # Run agent
    try:
        response, new_history = run_turn(message, profile, history)
    except Exception as e:
        return JSONResponse({
            "reply": f"Sorry, I had trouble processing that. Error: {type(e).__name__}",
            "trace": [],
            "guardrails": {},
        })

    # Update session messages
    chat_messages.append({"role": "user", "content": message})
    chat_messages.append({"role": "assistant", "content": response.reply})
    # Keep last 20 messages to avoid session bloat
    request.session["chat_messages"] = chat_messages[-20:]

    # Build trace for display
    trace = [
        {
            "idx": s.idx, "agent": s.agent, "action": s.action,
            "tool": s.tool_name or "", "result": s.result_summary or s.tool_args_summary or "",
            "ms": s.latency_ms,
        }
        for s in response.reasoning_trace
    ]

    return JSONResponse({
        "reply": response.reply,
        "trace": trace,
        "guardrails": response.guardrail_report.model_dump(),
    })


@app.get("/goals", response_class=HTMLResponse)
async def goals_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)
    profile = _get_profile(user_id)
    goals = list_goals(user_id)
    return templates.TemplateResponse(request, "goals.html", {
        "profile": profile,
        "goals": goals,
    })


@app.post("/goals/create")
async def create_goal_route(request: Request, name: str = Form(...), target_amount: float = Form(...), target_date: str = Form(None)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)
    profile = _get_profile(user_id)
    create_goal(user_id, name, target_amount, profile.currency, target_date or None)
    return RedirectResponse("/goals", status_code=302)


@app.post("/goals/simulate")
async def simulate_goal_route(request: Request, goal_name: str = Form(...), target_amount: float = Form(...), target_months: int = Form(6)):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    result = simulate_goal(user_id, goal_name, target_amount, target_months)
    return JSONResponse(result)


@app.get("/seed")
async def reseed(request: Request):
    seed_all()
    return RedirectResponse("/", status_code=302)


def start_server(port: int = 8000):
    """Start the web server."""
    import uvicorn
    print(f"Starting Saver web dashboard at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
