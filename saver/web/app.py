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
from saver.web.i18n import get_translations
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


def _get_lang(request: Request) -> str:
    return request.session.get("lang", "en")


def _ctx(request: Request, **kwargs) -> dict:
    """Build common template context with language/translations."""
    lang = _get_lang(request)
    return {"request": request, "lang": lang, "i18n": get_translations(lang), **kwargs}


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
        return RedirectResponse("/chat", status_code=302)
    with get_conn() as conn:
        users = conn.execute("SELECT user_id, name, market, currency FROM users").fetchall()
    lang = request.session.get("lang", "en")
    return templates.TemplateResponse(request, "login.html", {
        "request": request, "users": [dict(u) for u in users],
        "lang": lang, "i18n": get_translations(lang),
    })


@app.post("/login")
async def login(request: Request, user_id: str = Form(...)):
    profile = _get_profile(user_id)
    if not profile:
        return RedirectResponse("/", status_code=302)
    request.session["user_id"] = user_id
    request.session["user_name"] = profile.name
    request.session["chat_history"] = []
    # Default language to English, user can switch later
    if "lang" not in request.session:
        request.session["lang"] = "en"
    if not request.session.get("onboarding_complete"):
        return RedirectResponse("/onboarding", status_code=302)
    return RedirectResponse("/chat", status_code=302)


@app.post("/set-language")
async def set_language(request: Request, lang: str = Form(...)):
    if lang in ("en", "id"):
        request.session["lang"] = lang
    referer = request.headers.get("referer", "/dashboard")
    return RedirectResponse(referer, status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)
    if request.session.get("onboarding_complete"):
        return RedirectResponse("/chat", status_code=302)
    profile = _get_profile(user_id)
    return templates.TemplateResponse(request, "onboarding.html", _ctx(request, profile=profile))


@app.post("/onboarding/complete")
async def onboarding_complete(request: Request, worry: str = Form("")):
    request.session["onboarding_complete"] = True
    request.session["money_worry"] = worry
    return RedirectResponse("/chat", status_code=302)


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

    # Actionable intelligence
    from saver.tools.actionable import get_daily_target, get_earnings_efficiency, get_upcoming_bills, get_smart_savings_plan
    daily_target = get_daily_target(user_id)
    efficiency = get_earnings_efficiency(user_id, 7)
    bills = get_upcoming_bills(user_id)
    savings_plan = get_smart_savings_plan(user_id)

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

    return templates.TemplateResponse(request, "dashboard.html", _ctx(request,
        profile=profile,
        expenses=expenses,
        income=income,
        grab=grab,
        trips=trips,
        forecast=forecast,
        goals=goals,
        deltas=deltas,
        daily_target=daily_target,
        efficiency=efficiency,
        bills=bills,
        savings_plan=savings_plan,
    ))


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)
    profile = _get_profile(user_id)
    messages = request.session.get("chat_messages", [])
    return templates.TemplateResponse(request, "chat.html", _ctx(request,
        profile=profile,
        messages=messages,
    ))


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

    # Override profile language with session language (user may have switched)
    session_lang = request.session.get("lang", "en")
    profile.preferred_lang = session_lang

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


@app.get("/api/status")
async def get_status(request: Request):
    """Quick status data for the chat-first home status card."""
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = _get_profile(user_id)
    if not profile:
        return JSONResponse({"error": "User not found"}, status_code=404)

    from saver.tools.actionable import get_daily_target
    daily_target = get_daily_target(user_id)

    on_track = daily_target.get("still_needed_today", 0) <= 0
    today_amount = f"{profile.currency} {daily_target.get('daily_target', 0):,.0f}"
    if on_track:
        today_label = "Target reached!"
    else:
        today_label = f"{profile.currency} {daily_target.get('still_needed_today', 0):,.0f} more to go"

    return JSONResponse({
        "today_amount": today_amount,
        "today_label": today_label,
        "weekly_pct": daily_target.get("weekly_progress_pct", 0),
        "on_track": on_track,
    })


@app.get("/goals", response_class=HTMLResponse)
async def goals_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/", status_code=302)
    profile = _get_profile(user_id)
    goals = list_goals(user_id)
    return templates.TemplateResponse(request, "goals.html", _ctx(request,
        profile=profile,
        goals=goals,
    ))


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


@app.get("/api/insights")
async def get_insights(request: Request):
    """Generate AI-powered financial insights for the dashboard.

    Called async from the dashboard JS after page load, so the dashboard
    renders instantly and insights appear with a typing animation.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    profile = _get_profile(user_id)
    if not profile:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # Gather data for the LLM to reason over
    expenses = get_expense_breakdown(user_id, 7)
    expenses_prev = get_expense_breakdown(user_id, 14)
    income = get_income_summary(user_id, 30)
    grab = get_grab_earnings(user_id, 30)
    trips = get_grab_trip_summary(user_id, 7)
    forecast_data = forecast_cashflow(user_id, 14)
    goals_data = list_goals(user_id)

    # Build a focused prompt for insights generation
    from saver.agents.llm_config import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    import json as _json

    session_lang = request.session.get("lang", profile.preferred_lang)
    lang = "Bahasa Indonesia" if session_lang == "id" else "English"

    system_prompt = f"""You are Saver, a financial wellness coach for Grab partners. Generate exactly 3 short, actionable financial insights for the user based on their data below.

RULES:
- Each insight must be 1-2 sentences max
- Use ONLY numbers from the provided data — never invent figures
- Be warm, non-judgmental, and specific
- Include one positive observation, one area of concern, and one actionable suggestion
- Respond in {lang}
- Format as a JSON array of objects: [{{"icon": "emoji", "title": "short title", "body": "insight text", "type": "positive|warning|suggestion"}}]
- Only return the JSON array, nothing else

USER: {profile.name} ({profile.market.value} market, {profile.currency})"""

    data_summary = f"""DATA:
- Weekly spending: {profile.currency} {expenses['total']:,.0f} ({len(expenses['top_categories'])} categories)
- Previous 2-week avg spending: {profile.currency} {expenses_prev['total']/2:,.0f}/week
- Top expense: {expenses['top_categories'][0]['category'] if expenses['top_categories'] else 'none'} at {expenses['top_categories'][0]['percentage'] if expenses['top_categories'] else 0}%
- Monthly income: {profile.currency} {income['total_income']:,.0f}
- Grab gross (30d): {profile.currency} {grab['gross_earnings']:,.0f}, net: {profile.currency} {grab['net_earnings']:,.0f}, fees: {profile.currency} {grab['platform_fees']:,.0f}
- Trips this week: {trips['total_trips']}, hours: {trips['total_hours']}h, fuel ratio: {trips['fuel_ratio']*100:.0f}%
- 14-day forecast: min balance {profile.currency} {forecast_data['summary']['expected_min_balance']:,.0f}, negative prob: {forecast_data['summary']['probability_negative_balance']*100:.0f}%
- High-risk dates: {', '.join(forecast_data['summary']['high_risk_dates'][:3]) or 'none'}
- Active goals: {len([g for g in goals_data if g.get('status') == 'active'])}"""

    try:
        llm = get_llm()
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=data_summary),
        ])

        # Parse the JSON response
        content = response.content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        insights = _json.loads(content)
        return JSONResponse({"insights": insights})
    except Exception as e:
        logger.error("Insights generation failed: %s", str(e)[:200])
        # Return rule-based fallback insights
        fallback = []
        if expenses["total"] > 0 and expenses_prev["total"] > 0:
            delta = (expenses["total"] - expenses_prev["total"]/2) / (expenses_prev["total"]/2) * 100
            if delta > 15:
                fallback.append({"icon": "📊", "title": "Spending up", "body": f"Your spending is up {delta:.0f}% this week. Check if that matches busier work days.", "type": "warning"})
            elif delta < -10:
                fallback.append({"icon": "✅", "title": "Spending down", "body": f"Nice — spending is down {abs(delta):.0f}% this week. Keep it up!", "type": "positive"})

        if forecast_data["summary"]["probability_negative_balance"] > 0.3:
            fallback.append({"icon": "⚠️", "title": "Balance alert", "body": f"Your balance might go negative around {forecast_data['summary']['high_risk_dates'][0] if forecast_data['summary']['high_risk_dates'] else 'next week'}. Consider setting aside some savings.", "type": "warning"})

        if not goals_data or all(g.get("status") != "active" for g in goals_data):
            fallback.append({"icon": "🎯", "title": "Set a goal", "body": "You don't have any savings goals yet. Even a small weekly target builds up over time.", "type": "suggestion"})

        if not fallback:
            fallback = [{"icon": "👋", "title": "Welcome", "body": "Saver is analyzing your finances. Check back soon for personalized insights!", "type": "positive"}]

        return JSONResponse({"insights": fallback, "source": "fallback"})


@app.get("/seed")
async def reseed(request: Request):
    seed_all()
    return RedirectResponse("/", status_code=302)


def start_server(port: int = 8000):
    """Start the web server."""
    import uvicorn
    print(f"Starting Saver web dashboard at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
