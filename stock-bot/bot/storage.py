"""Append-only logging of bot activity to local SQLite, for the dashboard.

Kept deliberately simple: every loop tick appends rows for account snapshot,
trend readings and any orders placed. Nothing here ever deletes or mutates
history - the dashboard and any post-hoc review depend on the log being a
faithful record of what the bot actually saw and did.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bot.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS account_snapshots (
    ts TEXT NOT NULL,
    mode TEXT NOT NULL,
    equity REAL NOT NULL,
    cash REAL NOT NULL,
    last_equity REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trend_readings (
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal TEXT NOT NULL,
    price REAL NOT NULL,
    fast_sma REAL NOT NULL,
    slow_sma REAL NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    order_id TEXT,
    reason TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_account_snapshot(mode: str, equity: float, cash: float, last_equity: float) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO account_snapshots (ts, mode, equity, cash, last_equity) "
            "VALUES (?, ?, ?, ?, ?)",
            (_now(), mode, equity, cash, last_equity),
        )


def log_trend_reading(symbol: str, signal: str, price: float, fast_sma: float,
                       slow_sma: float, reason: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO trend_readings "
            "(ts, symbol, signal, price, fast_sma, slow_sma, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_now(), symbol, signal, price, fast_sma, slow_sma, reason),
        )


def log_order(symbol: str, side: str, qty: float, order_id: str | None,
              reason: str, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO orders (ts, symbol, side, qty, order_id, reason, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_now(), symbol, side, qty, order_id, reason, status),
        )


def log_event(level: str, message: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (ts, level, message) VALUES (?, ?, ?)",
            (_now(), level, message),
        )
    print(f"[{level.upper()}] {message}")
