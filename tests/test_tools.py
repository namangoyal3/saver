"""Tests for Saver tools."""

import pytest

from saver.data.db import init_db
from saver.data.seed import seed_all
from saver.tools.forecast import forecast_cashflow, simulate_goal
from saver.tools.goals import create_goal, list_goals, update_goal
from saver.tools.grab_earnings import get_grab_earnings, get_grab_trip_summary
from saver.tools.transactions import get_expense_breakdown, get_income_summary


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    seed_all()


class TestTransactions:
    def test_expense_breakdown_returns_categories(self):
        result = get_expense_breakdown("budi-001", 30)
        assert result["total"] > 0
        assert result["currency"] == "IDR"
        assert len(result["top_categories"]) > 0
        # Percentages should sum to ~100
        total_pct = sum(c["percentage"] for c in result["top_categories"])
        assert 99 <= total_pct <= 101

    def test_expense_breakdown_empty_user(self):
        result = get_expense_breakdown("nonexistent", 7)
        assert result["total"] == 0

    def test_income_summary(self):
        result = get_income_summary("siti-001", 30)
        assert result["total_income"] > 0
        assert result["currency"] == "SGD"
        assert result["avg_weekly"] > 0

    def test_income_summary_has_grab_payout(self):
        result = get_income_summary("budi-001", 30)
        assert "grab_payout" in result["source_breakdown"]


class TestGrabEarnings:
    def test_grab_earnings(self):
        result = get_grab_earnings("budi-001", 30)
        assert result["gross_earnings"] > 0
        assert result["platform_fees"] > 0
        assert result["net_earnings"] < result["gross_earnings"]

    def test_trip_summary(self):
        result = get_grab_trip_summary("siti-001", 7)
        assert result["total_trips"] > 0
        assert result["total_hours"] > 0


class TestForecast:
    def test_forecast_cashflow(self):
        result = forecast_cashflow("budi-001", 14)
        assert len(result["points"]) == 14
        assert "summary" in result
        assert "expected_min_balance" in result["summary"]

    def test_simulate_goal(self):
        result = simulate_goal("budi-001", "Test Goal", 5_000_000, 6)
        assert "feasible" in result
        assert "suggested_weekly_contribution" in result
        assert result["narrative"]  # non-empty


class TestGoals:
    def test_list_goals_siti(self):
        goals = list_goals("siti-001")
        assert len(goals) >= 1
        assert goals[0]["name"] == "Emergency Buffer"

    def test_create_and_update_goal(self):
        result = create_goal("budi-001", "Bike Repair Fund", 500_000, "IDR", "2026-12-31")
        assert result["status"] == "created"
        goal_id = result["goal_id"]

        updated = update_goal("budi-001", goal_id, status="paused")
        assert updated["status"] == "paused"  # returns the row's actual status

    def test_update_goal_wrong_user(self):
        result = create_goal("budi-001", "Test Auth", 100_000, "IDR")
        goal_id = result["goal_id"]
        # Try updating as wrong user
        updated = update_goal("siti-001", goal_id, status="paused")
        assert updated["status"] == "not_found"  # should be denied
