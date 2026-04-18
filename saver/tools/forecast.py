"""Cashflow forecasting tools — forecast_cashflow, simulate_goal."""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from saver.data.db import get_conn, get_cutoff_date, get_user_currency
from saver.models import (
    ForecastPoint,
    ForecastResult,
    ForecastSummary,
    SimulateGoalResult,
)


def _get_daily_net(user_id: str, lookback_days: int = 60) -> list[tuple[str, float]]:
    """Get daily net cashflow (credits - debits) for lookback window."""
    cutoff = get_cutoff_date(lookback_days)
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DATE(posted_at) as d,
                      SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) -
                      SUM(CASE WHEN direction='debit' THEN amount ELSE 0 END) as net
               FROM transactions
               WHERE user_id = ? AND posted_at >= ?
               GROUP BY DATE(posted_at)
               ORDER BY d""",
            (user_id, cutoff),
        ).fetchall()
    return [(r["d"], r["net"]) for r in rows]


def forecast_cashflow(user_id: str, horizon_days: int = 14) -> dict:
    """Naive seasonal forecast: use day-of-week averages from historical data."""
    currency = get_user_currency(user_id)

    daily_net = _get_daily_net(user_id, lookback_days=60)
    if len(daily_net) < 7:
        return ForecastResult(
            points=[], currency=currency,
            summary=ForecastSummary(expected_min_balance=0, probability_negative_balance=0.5, high_risk_dates=[]),
        ).model_dump()

    # Group by day-of-week
    dow_nets: dict[int, list[float]] = {i: [] for i in range(7)}
    for d_str, net in daily_net:
        d = date.fromisoformat(d_str)
        dow_nets[d.weekday()].append(net)

    # Compute per-DOW stats
    dow_stats: dict[int, tuple[float, float]] = {}
    for dow, vals in dow_nets.items():
        if vals:
            mu = statistics.mean(vals)
            sd = statistics.stdev(vals) if len(vals) > 1 else abs(mu) * 0.3
            dow_stats[dow] = (mu, sd)
        else:
            all_vals = [v for vs in dow_nets.values() for v in vs]
            mu = statistics.mean(all_vals) if all_vals else 0
            dow_stats[dow] = (mu, abs(mu) * 0.3)

    # Project forward
    points = []
    cumulative = 0.0
    min_balance = float("inf")
    high_risk = []
    neg_count = 0

    today = date.today()
    for i in range(1, horizon_days + 1):
        d = today + timedelta(days=i)
        mu, sd = dow_stats[d.weekday()]
        cumulative += mu
        p10 = cumulative - 1.28 * sd * (i ** 0.5)
        p90 = cumulative + 1.28 * sd * (i ** 0.5)

        points.append(ForecastPoint(
            date=d.isoformat(),
            net_p50=round(cumulative, 2),
            net_p10=round(p10, 2),
            net_p90=round(p90, 2),
            currency=currency,
        ))

        if cumulative < min_balance:
            min_balance = cumulative
        if p10 < 0:
            neg_count += 1
            high_risk.append(d.isoformat())

    prob_neg = round(neg_count / horizon_days, 2) if horizon_days > 0 else 0

    return ForecastResult(
        points=points,
        currency=currency,
        summary=ForecastSummary(
            expected_min_balance=round(min_balance, 2),
            probability_negative_balance=prob_neg,
            high_risk_dates=high_risk[:5],
        ),
    ).model_dump()


def simulate_goal(user_id: str, goal_name: str, target_amount: float, target_months: int = 6) -> dict:
    """Simulate whether a savings goal is feasible given historical cashflow.

    Uses MONTHLY surplus (not weekly) to properly account for monthly obligations
    like rent, insurance, and utilities that create artificial weekly volatility.
    """
    currency = get_user_currency(user_id)

    daily_net = _get_daily_net(user_id, lookback_days=60)
    if not daily_net:
        return SimulateGoalResult(
            feasible=False, suggested_weekly_contribution=0,
            risk_weeks=[], narrative="Not enough data to simulate.", currency=currency,
        ).model_dump()

    # Use MONTHLY aggregation to smooth out monthly-expense spikes
    # This gives a much more accurate picture than weekly
    total_net = sum(net for _, net in daily_net)
    num_days = len(daily_net)
    monthly_surplus = total_net / num_days * 30  # normalize to 30-day month
    weekly_surplus = monthly_surplus / 4.33

    # Monthly contribution needed
    monthly_needed = target_amount / max(target_months, 1)
    weekly_needed = round(monthly_needed / 4.33, 2)

    # Weekly aggregation for risk-week identification
    weekly_nets: list[float] = []
    week_sum = 0.0
    count = 0
    for _, net in daily_net:
        week_sum += net
        count += 1
        if count == 7:
            weekly_nets.append(week_sum)
            week_sum = 0.0
            count = 0
    if count > 0:
        weekly_nets.append(week_sum)

    # Risk weeks: where weekly net < weekly_needed even after smoothing
    risk_weeks = []
    for i, w in enumerate(weekly_nets):
        if w < weekly_needed:
            risk_weeks.append(f"week_{i+1}")

    # Feasibility: can we save this from the monthly surplus?
    feasible = monthly_needed <= monthly_surplus * 0.6  # 60% of surplus is safe

    # Suggest a safe amount
    safe_monthly = max(monthly_surplus * 0.4, 0)  # 40% of surplus
    suggested_weekly = round(safe_monthly / 4.33, 2)
    suggested_weekly = max(suggested_weekly, 0)

    # Calculate how long at the suggested rate
    if suggested_weekly > 0:
        weeks_at_suggested = target_amount / suggested_weekly
        months_at_suggested = round(weeks_at_suggested / 4.33, 1)
    else:
        months_at_suggested = 0

    pct_risk = round(len(risk_weeks) / max(len(weekly_nets), 1) * 100)

    if feasible:
        narrative = (
            f"Saving {currency} {weekly_needed:,.0f}/week for {goal_name} looks doable! "
            f"Your monthly surplus is about {currency} {monthly_surplus:,.0f}. "
            f"I'd suggest {currency} {suggested_weekly:,.0f}/week to stay comfortable — "
            f"about {pct_risk}% of weeks may be tighter due to monthly bills."
        )
    elif weekly_surplus > 0:
        narrative = (
            f"Saving {currency} {weekly_needed:,.0f}/week for {goal_name} is ambitious but possible. "
            f"Your monthly surplus is about {currency} {monthly_surplus:,.0f} after bills. "
            f"A comfortable pace: {currency} {suggested_weekly:,.0f}/week "
            f"— that would reach your target in about {months_at_suggested} months instead of {target_months}."
        )
    else:
        narrative = (
            f"Your current expenses are close to your income, making it hard to save for {goal_name} right now. "
            f"Let's focus on reducing expenses first — "
            f"even small cuts to your top spending categories could free up savings."
        )

    return SimulateGoalResult(
        feasible=feasible,
        suggested_weekly_contribution=suggested_weekly,
        risk_weeks=risk_weeks[:5],
        narrative=narrative,
        currency=currency,
    ).model_dump()
