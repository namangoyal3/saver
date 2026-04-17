"""Goal management tools — list_goals, create_goal, update_goal."""

from __future__ import annotations

import json
import logging
import uuid

from saver.data.db import get_conn

logger = logging.getLogger(__name__)

# Explicit allowlist for updatable columns — prevents SQL injection
_UPDATABLE_COLUMNS = frozenset({"status", "target_amount", "target_date", "current_amount", "contribution_plan", "name"})


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
    # Input validation
    if not name or len(name) > 100:
        return {"error": "Goal name must be 1-100 characters"}
    if target_amount <= 0:
        return {"error": "Target amount must be positive"}

    goal_id = str(uuid.uuid4())
    plan = json.dumps(contribution_plan or {"cadence": "weekly", "rule": "fixed"})

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO goals (goal_id, user_id, name, target_amount, current_amount, currency, target_date, status, contribution_plan)
               VALUES (?, ?, ?, ?, 0, ?, ?, 'active', ?)""",
            (goal_id, user_id, name, target_amount, currency, target_date, plan),
        )

    logger.info("Goal created: %s for user %s", goal_id, user_id)
    return {
        "goal_id": goal_id,
        "status": "created",
        "name": name,
        "target_amount": target_amount,
        "currency": currency,
    }


def update_goal(user_id: str, goal_id: str, **updates) -> dict:
    """Update a goal's status, target, or contribution plan.

    Requires user_id to verify ownership — prevents unauthorized access.
    """
    filtered = {k: v for k, v in updates.items() if k in _UPDATABLE_COLUMNS and v is not None}

    if not filtered:
        return {"goal_id": goal_id, "status": "no_changes"}

    if "contribution_plan" in filtered and isinstance(filtered["contribution_plan"], dict):
        filtered["contribution_plan"] = json.dumps(filtered["contribution_plan"])

    # Build safe SET clause using only allowlisted column names
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [goal_id, user_id]

    with get_conn() as conn:
        conn.execute(
            f"UPDATE goals SET {set_clause} WHERE goal_id = ? AND user_id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM goals WHERE goal_id = ? AND user_id = ?",
            (goal_id, user_id),
        ).fetchone()

    if not row:
        return {"goal_id": goal_id, "status": "not_found"}

    logger.info("Goal updated: %s for user %s", goal_id, user_id)
    result = dict(row)
    result["contribution_plan"] = json.loads(result["contribution_plan"]) if isinstance(result["contribution_plan"], str) else result["contribution_plan"]
    return result
