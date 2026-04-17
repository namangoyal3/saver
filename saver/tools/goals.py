"""Goal management tools — list_goals, create_goal, update_goal."""

from __future__ import annotations

import json
import uuid

from saver.data.db import get_conn
from saver.models import GoalRecord


def list_goals(user_id: str) -> list[dict]:
    """List all goals for a user."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM goals WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    results = []
    for r in rows:
        g = dict(r)
        g["contribution_plan"] = json.loads(g["contribution_plan"]) if isinstance(g["contribution_plan"], str) else g["contribution_plan"]
        results.append(g)
    return results


def create_goal(
    user_id: str,
    name: str,
    target_amount: float,
    currency: str,
    target_date: str | None = None,
    contribution_plan: dict | None = None,
) -> dict:
    """Create a new savings goal. Returns the created goal."""
    goal_id = str(uuid.uuid4())
    plan = json.dumps(contribution_plan or {"cadence": "weekly", "rule": "fixed"})

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO goals (goal_id, user_id, name, target_amount, current_amount, currency, target_date, status, contribution_plan)
               VALUES (?, ?, ?, ?, 0, ?, ?, 'active', ?)""",
            (goal_id, user_id, name, target_amount, currency, target_date, plan),
        )

    return {
        "goal_id": goal_id,
        "status": "created",
        "name": name,
        "target_amount": target_amount,
        "currency": currency,
    }


def update_goal(goal_id: str, **updates) -> dict:
    """Update a goal's status, target, or contribution plan."""
    allowed = {"status", "target_amount", "target_date", "current_amount", "contribution_plan", "name"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}

    if not filtered:
        return {"goal_id": goal_id, "status": "no_changes"}

    if "contribution_plan" in filtered and isinstance(filtered["contribution_plan"], dict):
        filtered["contribution_plan"] = json.dumps(filtered["contribution_plan"])

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [goal_id]

    with get_conn() as conn:
        conn.execute(f"UPDATE goals SET {set_clause} WHERE goal_id = ?", values)
        row = conn.execute("SELECT * FROM goals WHERE goal_id = ?", (goal_id,)).fetchone()

    if not row:
        return {"goal_id": goal_id, "status": "not_found"}

    return {"goal_id": goal_id, "status": "updated", **dict(row)}
