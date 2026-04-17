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
    """Simulate whether a savings goal is feasible given historical cashflow."""
    currency = get_user_currency(user_id)

    daily_net = _get_daily_net(user_id, lookback_days=60)
    if not daily_net:
        return SimulateGoalResult(
            feasible=False, suggested_weekly_contribution=0,
            risk_weeks=[], narrative="Not enough data to simulate.", currency=currency,
        ).model_dump()

    # Weekly aggregation
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

    avg_weekly_surplus = statistics.mean(weekly_nets) if weekly_nets else 0
    total_weeks = target_months * 4.33
    weekly_needed = round(target_amount / total_weeks, 2)

    # Find risk weeks (weeks where surplus < needed)
    risk_weeks = []
    for i, w in enumerate(weekly_nets):
        if w < weekly_needed:
            risk_weeks.append(f"week_{i+1}")

    feasible = weekly_needed <= avg_weekly_surplus * 0.7  # 70% of surplus is safe

    # Suggest adaptive amount
    suggested = min(weekly_needed, round(avg_weekly_surplus * 0.5, 2))
    suggested = max(suggested, 0)

    pct_risk = round(len(risk_weeks) / max(len(weekly_nets), 1) * 100)

    if feasible:
        narrative = (
            f"Saving {currency} {weekly_needed:,.0f}/week for {goal_name} looks doable. "
            f"Your average weekly surplus is {currency} {avg_weekly_surplus:,.0f}. "
            f"I'd suggest {currency} {suggested:,.0f}/week to be safe — "
            f"about {pct_risk}% of weeks might be tight."
        )
    else:
        narrative = (
            f"Saving {currency} {weekly_needed:,.0f}/week for {goal_name} would be a stretch. "
            f"Your average weekly surplus is only {currency} {avg_weekly_surplus:,.0f}. "
            f"A safer target: {currency} {suggested:,.0f}/week, which would take longer but won't stress your budget."
        )

    return SimulateGoalResult(
        feasible=feasible,
        suggested_weekly_contribution=suggested,
        risk_weeks=risk_weeks[:5],
        narrative=narrative,
        currency=currency,
    ).model_dump()
