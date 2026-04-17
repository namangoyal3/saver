"""SQLite database setup and queries — mirrors PRD §15.1 schemas."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("SAVER_DB_PATH", Path(__file__).parent.parent.parent / "data" / "saver.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    market       TEXT NOT NULL CHECK (market IN ('SG','ID')),
    preferred_lang TEXT NOT NULL DEFAULT 'en',
    partner_types TEXT NOT NULL,
    earnings_tier TEXT NOT NULL DEFAULT 'M',
    financial_persona TEXT NOT NULL DEFAULT 'stabilizer',
    currency     TEXT NOT NULL DEFAULT 'SGD',
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id       TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    posted_at    TEXT NOT NULL,
    amount       REAL NOT NULL,
    currency     TEXT NOT NULL,
    direction    TEXT CHECK (direction IN ('debit','credit')),
    category     TEXT,
    counterparty TEXT,
    channel      TEXT
);
CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, posted_at DESC);

CREATE TABLE IF NOT EXISTS grab_earnings (
    earning_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    date         TEXT NOT NULL,
    gross_earnings REAL NOT NULL,
    net_earnings REAL NOT NULL,
    platform_fees REAL NOT NULL DEFAULT 0,
    incentives   REAL NOT NULL DEFAULT 0,
    trips        INTEGER NOT NULL DEFAULT 0,
    hours        REAL NOT NULL DEFAULT 0,
    currency     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_earn_user_date ON grab_earnings(user_id, date DESC);

CREATE TABLE IF NOT EXISTS goals (
    goal_id      TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    name         TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0,
    currency     TEXT NOT NULL,
    target_date  TEXT,
    status       TEXT NOT NULL DEFAULT 'active',
    contribution_plan TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
"""


def init_db() -> None:
    """Create tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    """Yield a SQLite connection with row_factory = sqlite3.Row."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
