"""Actionable intelligence tools — the features that make Saver actually useful.

These tools go beyond reporting to give gig workers specific, concrete
actions they can take TODAY to improve their financial situation.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from saver.data.db import get_conn, get_cutoff_date, get_user_currency


def get_daily_target(user_id: str) -> dict:
    """Calculate today's earnings target based on weekly goal and what's been earned so far.

    This is the #1 feature a gig worker needs: a clear number to hit each day.
    """
    currency = get_user_currency(user_id)
    today = date.today()
    # Week starts Monday (weekday 0)
    days_into_week = today.weekday()
    week_start = (today - timedelta(days=days_into_week)).isoformat()

    with get_conn() as conn:
        # What have they earned this week so far?
        earned_this_week = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'credit'""",
            (user_id, week_start),
        ).fetchone()["total"]

        # What have they spent this week so far?
        spent_this_week = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'debit'""",
            (user_id, week_start),
        ).fetchone()["total"]

        # Historical weekly average (8 weeks)
        cutoff_8w = get_cutoff_date(56)
        weekly_avg = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) / 8.0 as avg_weekly
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'credit'""",
            (user_id, cutoff_8w),
        ).fetchone()["avg_weekly"]

        # Upcoming obligations this week (from monthly pattern)
        # Estimate weekly obligation = monthly expenses / 4.33
        monthly_expenses = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) / 2.0 as monthly_avg
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'debit'""",
            (user_id, get_cutoff_date(60)),
        ).fetchone()["monthly_avg"]

        # Active savings goals — weekly contribution needed
        goals = conn.execute(
            "SELECT target_amount, current_amount, target_date FROM goals WHERE user_id = ? AND status = 'active'",
            (user_id,),
        ).fetchall()

    weekly_goal_savings = 0.0
    for g in goals:
        remaining = g["target_amount"] - g["current_amount"]
        if remaining > 0 and g["target_date"]:
            days_left = max((date.fromisoformat(g["target_date"]) - today).days, 1)
            weekly_goal_savings += remaining / (days_left / 7)

    weekly_expense_target = monthly_expenses / 4.33
    weekly_target = weekly_expense_target + weekly_goal_savings
    days_left_in_week = max(7 - days_into_week, 1)
    remaining_to_earn = max(weekly_target - earned_this_week, 0)
    daily_target = round(remaining_to_earn / days_left_in_week, 0)

    # Today's earnings so far
    today_earned = 0.0
    with get_conn() as conn:
        today_earned = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ? AND DATE(posted_at) = ? AND direction = 'credit'""",
            (user_id, today.isoformat()),
        ).fetchone()["total"]

    still_needed = max(daily_target - today_earned, 0)

    return {
        "currency": currency,
        "daily_target": round(daily_target, 0),
        "earned_today": round(today_earned, 0),
        "still_needed_today": round(still_needed, 0),
        "earned_this_week": round(earned_this_week, 0),
        "weekly_target": round(weekly_target, 0),
        "weekly_progress_pct": round(earned_this_week / weekly_target * 100, 1) if weekly_target > 0 else 0,
        "days_left_in_week": days_left_in_week,
        "includes_goal_savings": round(weekly_goal_savings, 0),
    }


def get_earnings_efficiency(user_id: str, window_days: int = 7) -> dict:
    """Calculate earnings efficiency metrics — cost per trip, earnings per hour, fuel efficiency.

    Helps drivers optimize: "You're spending IDR 6.5k fuel per trip vs your 5.2k average."
    """
    currency = get_user_currency(user_id)
    cutoff = get_cutoff_date(window_days)
    cutoff_prev = get_cutoff_date(window_days * 2)

    with get_conn() as conn:
        # Current period
        current = conn.execute(
            """SELECT COALESCE(SUM(gross_earnings), 0) as gross,
                      COALESCE(SUM(net_earnings), 0) as net,
                      COALESCE(SUM(trips), 0) as trips,
                      COALESCE(SUM(hours), 0) as hours,
                      COALESCE(SUM(platform_fees), 0) as fees
               FROM grab_earnings WHERE user_id = ? AND date >= ?""",
            (user_id, cutoff),
        ).fetchone()

        # Previous period for comparison
        prev = conn.execute(
            """SELECT COALESCE(SUM(gross_earnings), 0) as gross,
                      COALESCE(SUM(net_earnings), 0) as net,
                      COALESCE(SUM(trips), 0) as trips,
                      COALESCE(SUM(hours), 0) as hours
               FROM grab_earnings WHERE user_id = ? AND date >= ? AND date < ?""",
            (user_id, cutoff_prev, cutoff),
        ).fetchone()

        # Fuel cost
        fuel_cost = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'debit'
                     AND category IN ('fuel', 'parking_tolls')""",
            (user_id, cutoff),
        ).fetchone()["total"]

        # Food on road cost
        food_cost = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'debit'
                     AND category = 'food_on_road'""",
            (user_id, cutoff),
        ).fetchone()["total"]

    trips = current["trips"] or 1
    hours = current["hours"] or 1
    prev_trips = prev["trips"] or 1
    prev_hours = prev["hours"] or 1

    earnings_per_hour = round(current["net"] / hours, 2)
    earnings_per_trip = round(current["net"] / trips, 2)
    fuel_per_trip = round(fuel_cost / trips, 2)
    food_per_trip = round(food_cost / trips, 2)
    total_cost_per_trip = round((fuel_cost + food_cost + current["fees"]) / trips, 2)
    profit_per_trip = round(current["gross"] / trips - total_cost_per_trip, 2)

    # Previous period comparisons
    prev_earnings_per_hour = round(prev["net"] / prev_hours, 2) if prev_hours else 0
    prev_earnings_per_trip = round(prev["net"] / prev_trips, 2) if prev_trips else 0

    # Optimization suggestions
    suggestions = []
    if fuel_per_trip > 0 and food_per_trip > 0:
        # If food cost is high relative to fuel
        if food_cost > fuel_cost * 0.6:
            potential_save = round(food_cost * 0.3, 0)  # 30% reduction
            suggestions.append({
                "type": "food_optimization",
                "message": f"Food on road costs {currency} {food_cost:,.0f}/week ({currency} {food_per_trip:,.0f}/trip). Packing meals 3 days could save ~{currency} {potential_save:,.0f}/week.",
                "potential_weekly_saving": potential_save,
            })

    if earnings_per_hour > 0 and prev_earnings_per_hour > 0:
        if earnings_per_hour < prev_earnings_per_hour * 0.9:
            suggestions.append({
                "type": "earnings_drop",
                "message": f"Your earnings per hour dropped from {currency} {prev_earnings_per_hour:,.0f} to {currency} {earnings_per_hour:,.0f}. Consider shifting to peak hours.",
                "potential_weekly_saving": 0,
            })

    if current["fees"] > 0:
        fee_pct = round(current["fees"] / current["gross"] * 100, 1) if current["gross"] else 0
        if fee_pct > 22:
            suggestions.append({
                "type": "platform_fees",
                "message": f"Platform fees are {fee_pct}% of your gross. Check if you qualify for any fee reduction programs.",
                "potential_weekly_saving": 0,
            })

    return {
        "currency": currency,
        "window_days": window_days,
        "earnings_per_hour": earnings_per_hour,
        "earnings_per_trip": earnings_per_trip,
        "fuel_per_trip": fuel_per_trip,
        "food_per_trip": food_per_trip,
        "total_cost_per_trip": total_cost_per_trip,
        "profit_per_trip": profit_per_trip,
        "total_trips": current["trips"],
        "total_hours": round(current["hours"], 1),
        "prev_earnings_per_hour": prev_earnings_per_hour,
        "prev_earnings_per_trip": prev_earnings_per_trip,
        "suggestions": suggestions,
    }


def get_upcoming_bills(user_id: str) -> dict:
    """Predict upcoming bills based on historical monthly patterns.

    "Rent due in 5 days. You have IDR 600k. You need IDR 200k more."
    """
    currency = get_user_currency(user_id)
    today = date.today()

    with get_conn() as conn:
        # Find recurring monthly expenses (appear in same category each month)
        monthly_patterns = conn.execute(
            """SELECT category, ROUND(AVG(amount), 0) as avg_amount,
                      MAX(CAST(strftime('%d', posted_at) AS INTEGER)) as typical_day
               FROM transactions
               WHERE user_id = ? AND direction = 'debit'
                     AND channel = 'auto_debit'
                     AND posted_at >= ?
               GROUP BY category
               HAVING COUNT(*) >= 2""",
            (user_id, get_cutoff_date(90)),
        ).fetchall()

        # Also find large weekly recurring (remittance, groceries)
        weekly_patterns = conn.execute(
            """SELECT category, ROUND(AVG(amount), 0) as avg_amount
               FROM transactions
               WHERE user_id = ? AND direction = 'debit'
                     AND category IN ('remittance', 'groceries')
                     AND posted_at >= ?
               GROUP BY category
               HAVING COUNT(*) >= 4""",
            (user_id, get_cutoff_date(60)),
        ).fetchall()

        # Current balance proxy (net of last 7 days)
        recent_net = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END), 0) -
                 COALESCE(SUM(CASE WHEN direction='debit' THEN amount ELSE 0 END), 0) as balance
               FROM transactions
               WHERE user_id = ? AND posted_at >= ?""",
            (user_id, get_cutoff_date(7)),
        ).fetchone()["balance"]

    bills = []
    for row in monthly_patterns:
        typical_day = row["typical_day"] or 1
        # Next occurrence
        if today.day <= typical_day:
            next_date = today.replace(day=min(typical_day, 28))
        else:
            next_month = today.month + 1 if today.month < 12 else 1
            next_year = today.year if today.month < 12 else today.year + 1
            next_date = date(next_year, next_month, min(typical_day, 28))

        days_until = (next_date - today).days
        if days_until <= 30:  # Only show upcoming within 30 days
            bills.append({
                "category": row["category"],
                "amount": row["avg_amount"],
                "due_date": next_date.isoformat(),
                "days_until": days_until,
                "urgency": "urgent" if days_until <= 5 else "upcoming" if days_until <= 14 else "planned",
            })

    # Sort by urgency (days_until)
    bills.sort(key=lambda b: b["days_until"])

    total_upcoming = sum(b["amount"] for b in bills)
    shortfall = max(total_upcoming - max(recent_net, 0), 0)

    return {
        "currency": currency,
        "bills": bills,
        "total_upcoming_30d": round(total_upcoming, 0),
        "estimated_available": round(max(recent_net, 0), 0),
        "shortfall": round(shortfall, 0),
        "has_shortfall": shortfall > 0,
    }


def get_smart_savings_plan(user_id: str) -> dict:
    """Generate a smart auto-save recommendation based on daily earnings patterns.

    "On days you earn above IDR 200k, auto-save IDR 20k. Skip on days below IDR 150k."
    """
    currency = get_user_currency(user_id)

    with get_conn() as conn:
        # Daily earnings for last 30 days
        daily_earnings = conn.execute(
            """SELECT DATE(posted_at) as d, SUM(amount) as daily_total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'credit'
               GROUP BY DATE(posted_at)
               ORDER BY d""",
            (user_id, get_cutoff_date(30)),
        ).fetchall()

    if len(daily_earnings) < 7:
        return {
            "currency": currency,
            "has_plan": False,
            "message": "Need more earnings history to create a smart savings plan.",
        }

    amounts = [r["daily_total"] for r in daily_earnings]
    avg_daily = statistics.mean(amounts)
    median_daily = statistics.median(amounts)
    p75 = sorted(amounts)[int(len(amounts) * 0.75)]
    p25 = sorted(amounts)[int(len(amounts) * 0.25)]

    # Good day threshold: above 75th percentile
    good_day_threshold = round(p75, 0)
    # Bad day threshold: below 25th percentile
    bad_day_threshold = round(p25, 0)
    # Normal day: between 25th and 75th

    # Auto-save amounts
    good_day_save = round(avg_daily * 0.15, 0)   # Save 15% on good days
    normal_day_save = round(avg_daily * 0.08, 0)  # Save 8% on normal days
    bad_day_save = 0  # Skip on bad days

    # Project monthly savings
    good_days_per_month = len([a for a in amounts if a >= good_day_threshold]) / len(amounts) * 30
    normal_days_per_month = len([a for a in amounts if p25 <= a < p75]) / len(amounts) * 30
    projected_monthly = round(good_day_save * good_days_per_month + normal_day_save * normal_days_per_month, 0)
    projected_yearly = projected_monthly * 12

    return {
        "currency": currency,
        "has_plan": True,
        "rules": [
            {
                "condition": f"Earn above {currency} {good_day_threshold:,.0f}",
                "action": f"Auto-save {currency} {good_day_save:,.0f}",
                "label": "Good day",
                "emoji": "🟢",
            },
            {
                "condition": f"Earn {currency} {bad_day_threshold:,.0f}–{good_day_threshold:,.0f}",
                "action": f"Auto-save {currency} {normal_day_save:,.0f}",
                "label": "Normal day",
                "emoji": "🟡",
            },
            {
                "condition": f"Earn below {currency} {bad_day_threshold:,.0f}",
                "action": "Skip saving (protect your buffer)",
                "label": "Tough day",
                "emoji": "🔴",
            },
        ],
        "projected_monthly_savings": projected_monthly,
        "projected_yearly_savings": projected_yearly,
        "avg_daily_earnings": round(avg_daily, 0),
        "good_day_threshold": good_day_threshold,
        "bad_day_threshold": bad_day_threshold,
    }
