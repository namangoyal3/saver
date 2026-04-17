"""Transaction analysis tools — get_transactions, get_expense_breakdown, get_income_summary."""

from __future__ import annotations

from saver.data.db import get_conn, get_cutoff_date, get_user_currency
from saver.models import ExpenseBreakdownResult, ExpenseCategory, IncomeSummaryResult


def get_transactions(user_id: str, window_days: int = 30, direction: str | None = None) -> list[dict]:
    """Fetch raw transactions for a user within a time window."""
    cutoff = get_cutoff_date(window_days)
    with get_conn() as conn:
        if direction:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? AND posted_at >= ? AND direction = ? ORDER BY posted_at DESC",
                (user_id, cutoff, direction),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? AND posted_at >= ? ORDER BY posted_at DESC",
                (user_id, cutoff),
            ).fetchall()
    return [dict(r) for r in rows]


def get_expense_breakdown(user_id: str, window_days: int = 7) -> dict:
    """Categorized expense breakdown for a user over a window."""
    cutoff = get_cutoff_date(window_days)
    currency = get_user_currency(user_id)

    with get_conn() as conn:
        rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'debit'
               GROUP BY category
               ORDER BY total DESC""",
            (user_id, cutoff),
        ).fetchall()

    total = sum(r["total"] for r in rows)
    if total == 0:
        return ExpenseBreakdownResult(
            total=0, currency=currency, window_days=window_days, top_categories=[]
        ).model_dump()

    categories = [
        ExpenseCategory(
            category=r["category"] or "uncategorized",
            amount=round(r["total"], 2),
            percentage=round(r["total"] / total * 100, 1),
        )
        for r in rows
    ]

    return ExpenseBreakdownResult(
        total=round(total, 2),
        currency=currency,
        window_days=window_days,
        top_categories=categories,
    ).model_dump()


def get_income_summary(user_id: str, window_days: int = 30) -> dict:
    """Income summary with source breakdown."""
    cutoff = get_cutoff_date(window_days)
    currency = get_user_currency(user_id)

    with get_conn() as conn:
        rows = conn.execute(
            """SELECT channel, SUM(amount) as total
               FROM transactions
               WHERE user_id = ? AND posted_at >= ? AND direction = 'credit'
               GROUP BY channel""",
            (user_id, cutoff),
        ).fetchall()

    total = sum(r["total"] for r in rows)
    weeks = max(window_days / 7, 1)
    sources = {r["channel"] or "other": round(r["total"], 2) for r in rows}

    return IncomeSummaryResult(
        total_income=round(total, 2),
        currency=currency,
        window_days=window_days,
        avg_weekly=round(total / weeks, 2),
        source_breakdown=sources,
    ).model_dump()
