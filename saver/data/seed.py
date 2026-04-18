"""Generate 90 days of synthetic data for Budi (Jakarta) and Siti (Singapore)."""

from __future__ import annotations

import json
import random
import uuid
from datetime import date, datetime, timedelta

from saver.data.db import get_conn, init_db

random.seed(42)

# ── Personas ───────────────────────────────────────────────────────────

PERSONAS = {
    "budi": {
        "user_id": "budi-001",
        "name": "Budi",
        "market": "ID",
        "preferred_lang": "id",
        "partner_types": "delivery",
        "earnings_tier": "L",
        "financial_persona": "firefighter",
        "currency": "IDR",
        # Earnings: IDR 4.5M-7M/month → ~150k-230k/day
        "daily_earnings_range": (150_000, 230_000),
        "platform_fee_pct": 0.20,
        "incentive_pct": 0.05,
        "trips_per_day_range": (10, 18),
        "hours_per_day_range": (5.0, 9.0),
        # Spending patterns
        "expense_categories": {
            "fuel": (15_000, 25_000),         # daily
            "food_on_road": (8_000, 18_000),
            "data_top_up": (0, 5_000),
            "remittance": (0, 0),             # weekly lump
            "vehicle_maintenance": (0, 0),    # occasional
            "groceries": (0, 0),              # weekly
            "other": (3_000, 10_000),
        },
        "weekly_expenses": {
            "remittance": (200_000, 300_000),
            "groceries": (100_000, 200_000),
        },
        "monthly_expenses": {
            "rent": (800_000, 800_000),
            "vehicle_maintenance": (100_000, 300_000),
        },
    },
    "siti": {
        "user_id": "siti-001",
        "name": "Siti",
        "market": "SG",
        "preferred_lang": "en",
        "partner_types": "ride",
        "earnings_tier": "M",
        "financial_persona": "stabilizer",
        "currency": "SGD",
        # Earnings: SGD 4000-5500/month → ~155-210/day (realistic for SG ride-hail)
        "daily_earnings_range": (155, 210),
        "platform_fee_pct": 0.20,
        "incentive_pct": 0.05,
        "trips_per_day_range": (8, 14),
        "hours_per_day_range": (7.0, 11.0),
        "expense_categories": {
            "fuel": (15, 25),
            "food_on_road": (6, 12),
            "parking_tolls": (2, 6),
            "phone_data": (0, 2),
            "other": (3, 10),
        },
        "weekly_expenses": {
            "groceries": (40, 70),
        },
        "monthly_expenses": {
            "rent": (650, 650),
            "insurance": (100, 100),
            "utilities": (50, 70),
            "child_education": (150, 150),
            "parent_allowance": (200, 200),
        },
    },
}


def _gen_daily_txns(persona: dict, d: date) -> list[dict]:
    """Generate transactions for a single day."""
    txns = []
    uid = persona["user_id"]
    cur = persona["currency"]
    dow = d.weekday()  # 0=Mon

    # Skip ~1 day/week (rest day) — different day per persona
    rest_day = 0 if persona["market"] == "ID" else 6  # Mon for Budi, Sun for Siti
    if dow == rest_day:
        # Still have some personal expenses on rest day
        for cat, (lo, hi) in persona["expense_categories"].items():
            if cat in ("food_on_road", "fuel", "parking_tolls"):
                continue  # no work expenses
            if lo == 0 and hi == 0:
                continue
            if random.random() < 0.4:
                amt = round(random.uniform(lo, hi), 2)
                txns.append({
                    "txn_id": str(uuid.uuid4()),
                    "user_id": uid,
                    "posted_at": datetime(d.year, d.month, d.day, random.randint(8, 21), random.randint(0, 59)).isoformat(),
                    "amount": amt,
                    "currency": cur,
                    "direction": "debit",
                    "category": cat,
                    "counterparty": f"{cat}_vendor",
                    "channel": "debit_card",
                })
        return txns

    # ── Earnings (single daily payout) ──
    base = random.uniform(*persona["daily_earnings_range"])
    # Add some weekly seasonality: weekends earn more
    if dow in (4, 5):  # Fri/Sat
        base *= random.uniform(1.1, 1.25)
    elif dow == 6:
        base *= random.uniform(1.05, 1.15)

    # Add occasional bad days
    if random.random() < 0.08:
        base *= random.uniform(0.4, 0.6)

    gross = round(base, 2)
    txns.append({
        "txn_id": str(uuid.uuid4()),
        "user_id": uid,
        "posted_at": datetime(d.year, d.month, d.day, 22, 0).isoformat(),
        "amount": gross,
        "currency": cur,
        "direction": "credit",
        "category": "grab_payout",
        "counterparty": "Grab",
        "channel": "grab_payout",
    })

    # ── Daily expenses ──
    for cat, (lo, hi) in persona["expense_categories"].items():
        if lo == 0 and hi == 0:
            continue
        if random.random() < 0.85:  # 85% chance of daily expense
            amt = round(random.uniform(lo, hi), 2)
            hour = random.randint(6, 20)
            txns.append({
                "txn_id": str(uuid.uuid4()),
                "user_id": uid,
                "posted_at": datetime(d.year, d.month, d.day, hour, random.randint(0, 59)).isoformat(),
                "amount": amt,
                "currency": cur,
                "direction": "debit",
                "category": cat,
                "counterparty": f"{cat}_vendor",
                "channel": "debit_card",
            })

    # ── Weekly expenses (on payout day = Friday) ──
    if dow == 4:
        for cat, (lo, hi) in persona.get("weekly_expenses", {}).items():
            amt = round(random.uniform(lo, hi), 2)
            txns.append({
                "txn_id": str(uuid.uuid4()),
                "user_id": uid,
                "posted_at": datetime(d.year, d.month, d.day, 12, 0).isoformat(),
                "amount": amt,
                "currency": cur,
                "direction": "debit",
                "category": cat,
                "counterparty": f"{cat}_vendor",
                "channel": "transfer" if cat == "remittance" else "debit_card",
            })

    # ── Monthly expenses (on the 1st or closest working day) ──
    if d.day <= 3 and dow not in (5, 6):
        for cat, (lo, hi) in persona.get("monthly_expenses", {}).items():
            amt = round(random.uniform(lo, hi), 2)
            txns.append({
                "txn_id": str(uuid.uuid4()),
                "user_id": uid,
                "posted_at": datetime(d.year, d.month, d.day, 10, 0).isoformat(),
                "amount": amt,
                "currency": cur,
                "direction": "debit",
                "category": cat,
                "counterparty": f"{cat}_vendor",
                "channel": "auto_debit",
            })

    return txns


def _gen_daily_earnings(persona: dict, d: date, txns: list[dict]) -> dict | None:
    """Generate a grab_earnings row from the day's payout transaction."""
    payout = next((t for t in txns if t["direction"] == "credit" and t["category"] == "grab_payout"), None)
    if not payout:
        return None

    gross = payout["amount"]
    fees = round(gross * persona["platform_fee_pct"], 2)
    incentives = round(gross * persona["incentive_pct"] * (1 if random.random() < 0.3 else 0), 2)
    net = round(gross - fees + incentives, 2)
    trips = random.randint(*persona["trips_per_day_range"])
    hours = round(random.uniform(*persona["hours_per_day_range"]), 1)

    return {
        "earning_id": str(uuid.uuid4()),
        "user_id": persona["user_id"],
        "date": d.isoformat(),
        "gross_earnings": gross,
        "net_earnings": net,
        "platform_fees": fees,
        "incentives": incentives,
        "trips": trips,
        "hours": hours,
        "currency": persona["currency"],
    }


def seed_all():
    """Generate and insert all synthetic data."""
    init_db()

    today = date.today()
    start = today - timedelta(days=90)

    with get_conn() as conn:
        # Clear existing data
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM grab_earnings")
        conn.execute("DELETE FROM goals")
        conn.execute("DELETE FROM users")

        for key, persona in PERSONAS.items():
            # Insert user
            conn.execute(
                "INSERT INTO users (user_id, name, market, preferred_lang, partner_types, earnings_tier, financial_persona, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (persona["user_id"], persona["name"], persona["market"], persona["preferred_lang"],
                 persona["partner_types"], persona["earnings_tier"], persona["financial_persona"], persona["currency"]),
            )

            # Generate 90 days of data
            all_txns = []
            all_earnings = []
            d = start
            while d <= today:
                day_txns = _gen_daily_txns(persona, d)
                all_txns.extend(day_txns)

                earning = _gen_daily_earnings(persona, d, day_txns)
                if earning:
                    all_earnings.append(earning)

                d += timedelta(days=1)

            # Bulk insert transactions
            conn.executemany(
                "INSERT INTO transactions (txn_id, user_id, posted_at, amount, currency, direction, category, counterparty, channel) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(t["txn_id"], t["user_id"], t["posted_at"], t["amount"], t["currency"],
                  t["direction"], t["category"], t["counterparty"], t["channel"]) for t in all_txns],
            )

            # Bulk insert earnings
            conn.executemany(
                "INSERT INTO grab_earnings (earning_id, user_id, date, gross_earnings, net_earnings, platform_fees, incentives, trips, hours, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(e["earning_id"], e["user_id"], e["date"], e["gross_earnings"], e["net_earnings"],
                  e["platform_fees"], e["incentives"], e["trips"], e["hours"], e["currency"]) for e in all_earnings],
            )

            # Add a sample goal for Siti
            if key == "siti":
                conn.execute(
                    "INSERT INTO goals (goal_id, user_id, name, target_amount, current_amount, currency, target_date, status, contribution_plan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), persona["user_id"], "Emergency Buffer",
                     3000.0, 850.0, "SGD", "2026-12-31", "active",
                     json.dumps({"cadence": "weekly", "rule": "fixed", "params": {"amount": 50}})),
                )

            print(f"  Seeded {persona['name']}: {len(all_txns)} transactions, {len(all_earnings)} earnings days")

    print("Seed complete.")


if __name__ == "__main__":
    seed_all()
