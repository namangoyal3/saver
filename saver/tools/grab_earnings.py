"""Grab earnings & trip tools — get_grab_earnings, get_grab_trip_summary."""

from __future__ import annotations

from saver.data.db import get_conn, get_cutoff_date, get_user_currency
from saver.models import GrabEarningsResult, GrabTripSummaryResult


def get_grab_earnings(user_id: str, window_days: int = 30) -> dict:
    """Aggregate Grab earnings over a window."""
    cutoff = get_cutoff_date(window_days)
    with get_conn() as conn:
        row = conn.execute(
            """SELECT SUM(gross_earnings) as gross, SUM(net_earnings) as net,
                      SUM(platform_fees) as fees, SUM(incentives) as incentives,
                      currency
               FROM grab_earnings
               WHERE user_id = ? AND date >= ?
               GROUP BY currency""",
            (user_id, cutoff),
        ).fetchone()

    if not row or row["gross"] is None:
        currency = get_user_currency(user_id)
        return GrabEarningsResult(
            gross_earnings=0, net_earnings=0, currency=currency,
            window_days=window_days, platform_fees=0, incentives=0
        ).model_dump()

    return GrabEarningsResult(
        gross_earnings=round(row["gross"], 2),
        net_earnings=round(row["net"], 2),
        currency=row["currency"],
        window_days=window_days,
        platform_fees=round(row["fees"], 2),
        incentives=round(row["incentives"], 2),
    ).model_dump()


def get_grab_trip_summary(user_id: str, window_days: int = 7) -> dict:
    """Trip count, hours, and efficiency metrics."""
    cutoff = get_cutoff_date(window_days)
    currency = get_user_currency(user_id)

    with get_conn() as conn:
        row = conn.execute(
            """SELECT SUM(trips) as total_trips, SUM(hours) as total_hours,
                      AVG(gross_earnings / NULLIF(trips, 0)) as avg_per_trip
               FROM grab_earnings
               WHERE user_id = ? AND date >= ?""",
            (user_id, cutoff),
        ).fetchone()

        # fuel ratio: fuel expenses / gross earnings
        fuel_expense = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as fuel
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'debit'
                     AND category IN ('fuel', 'parking_tolls')""",
            (user_id, cutoff),
        ).fetchone()

        gross = conn.execute(
            "SELECT COALESCE(SUM(gross_earnings), 0) as g FROM grab_earnings WHERE user_id = ? AND date >= ?",
            (user_id, cutoff),
        ).fetchone()

    total_trips = row["total_trips"] or 0
    total_hours = row["total_hours"] or 0
    avg_per = row["avg_per_trip"] or 0
    fuel_r = round(fuel_expense["fuel"] / gross["g"], 2) if gross["g"] else 0

    return GrabTripSummaryResult(
        total_trips=total_trips,
        total_hours=round(total_hours, 1),
        avg_earnings_per_trip=round(avg_per, 2),
        fuel_ratio=fuel_r,
        currency=currency,
        window_days=window_days,
    ).model_dump()
