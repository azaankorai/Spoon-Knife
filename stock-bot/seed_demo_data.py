#!/usr/bin/env python3
"""Fill data/bot.sqlite3 with realistic-looking sample data so you can preview
the dashboard without an Alpaca account or any real trading activity.

Usage:
    python seed_demo_data.py          # adds demo data (keeps any real data too)
    python seed_demo_data.py --reset  # wipes the DB first, then seeds fresh demo data

This writes through the exact same bot.storage module the live bot uses, so
the dashboard renders identically to how it would with real activity. Every
row is clearly fake - explore the dashboard, then run `python run.py` for the
real thing once your .env is configured.
"""
from __future__ import annotations

import argparse
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot import storage

random.seed(7)  # reproducible demo data

SYMBOLS = ["AAPL", "MSFT", "SPY"]
STARTING_EQUITY = 100_000.0
DAYS = 14
TICKS_PER_DAY = 6  # roughly one snapshot every ~65 minutes of a 6.5h session


def reset_db() -> None:
    if storage.DB_PATH.exists():
        storage.DB_PATH.unlink()
        print(f"Removed existing {storage.DB_PATH}")


def seed() -> None:
    storage.log_event(
        "info",
        "=== DEMO DATA: everything below this line is simulated for dashboard "
        "preview purposes - it is not real trading activity. ===",
    )

    base_prices = {"AAPL": 195.0, "MSFT": 415.0, "SPY": 545.0}
    price_history = {s: [] for s in SYMBOLS}
    equity = STARTING_EQUITY
    day_open_equity = equity
    open_positions: dict[str, dict] = {}

    start = datetime.now(timezone.utc) - timedelta(days=DAYS)

    for day in range(DAYS):
        day_open_equity = equity
        for tick in range(TICKS_PER_DAY):
            ts = start + timedelta(days=day, hours=tick * 1.1)
            _backdated(ts)

            # Each symbol drifts with a bit of trend + noise so crossovers occur.
            for symbol in SYMBOLS:
                drift = math.sin((day * TICKS_PER_DAY + tick) / 9.0) * 0.004
                noise = random.uniform(-0.006, 0.006)
                base_prices[symbol] *= (1 + drift + noise)
                price = round(base_prices[symbol], 2)
                price_history[symbol].append(price)

                fast = _sma(price_history[symbol], 5)
                slow = _sma(price_history[symbol], 12)
                if fast is None or slow is None:
                    continue

                signal, reason = _signal(price_history[symbol], 5, 12)
                storage.log_trend_reading(
                    symbol=symbol, signal=signal, price=price,
                    fast_sma=fast, slow_sma=slow, reason=reason,
                )

                if signal == "buy" and symbol not in open_positions:
                    qty = round((equity * 0.10) / price, 4)
                    cost = qty * price
                    equity -= 0  # cash moves into the position; equity unaffected at entry
                    open_positions[symbol] = {"qty": qty, "entry": price}
                    order_id = f"demo-{symbol}-{ts:%Y%m%d%H%M}"
                    storage.log_order(symbol=symbol, side="buy", qty=qty,
                                      order_id=order_id, reason=reason, status="filled")
                    storage.log_event("info",
                                      f"DEMO BUY {qty} {symbol} @ {price:.2f} - {reason}")

                elif signal == "sell" and symbol in open_positions:
                    pos = open_positions.pop(symbol)
                    pl = (price - pos["entry"]) * pos["qty"]
                    equity += pl
                    order_id = f"demo-{symbol}-{ts:%Y%m%d%H%M}"
                    storage.log_order(symbol=symbol, side="sell", qty=pos["qty"],
                                      order_id=order_id, reason=reason, status="filled")
                    storage.log_event(
                        "info",
                        f"DEMO SELL {pos['qty']} {symbol} @ {price:.2f} "
                        f"(P&L {pl:+.2f}) - {reason}",
                    )

            # Mark open positions to market for the equity snapshot.
            unrealized = sum(
                (price_history[sym][-1] - pos["entry"]) * pos["qty"]
                for sym, pos in open_positions.items()
            )
            cash = equity - sum(pos["qty"] * pos["entry"] for pos in open_positions.values())
            snapshot_equity = equity + unrealized
            storage.log_account_snapshot(
                mode="DEMO (seeded sample data - not real)",
                equity=round(snapshot_equity, 2),
                cash=round(cash, 2),
                last_equity=round(day_open_equity, 2),
            )

        # Occasionally simulate the circuit breaker tripping, purely for preview.
        if day == DAYS - 3:
            storage.log_event(
                "critical",
                "DEMO: simulated daily-loss circuit breaker trip for preview "
                "purposes (not a real event).",
            )

    storage.log_event(
        "info",
        "=== END OF DEMO DATA. Run `python run.py` with real Alpaca keys to "
        "replace this with genuine activity (use --reset on this script first). ===",
    )


def _sma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _signal(prices: list[float], fast_period: int, slow_period: int) -> tuple[str, str]:
    if len(prices) < slow_period + 1:
        return "hold", "not enough history yet"
    fast_now, fast_prev = _sma(prices, fast_period), _sma(prices[:-1], fast_period)
    slow_now, slow_prev = _sma(prices, slow_period), _sma(prices[:-1], slow_period)
    if fast_prev <= slow_prev and fast_now > slow_now:
        return "buy", f"{fast_period}-period SMA crossed above {slow_period}-period SMA (golden cross)"
    if fast_prev >= slow_prev and fast_now < slow_now:
        return "sell", f"{fast_period}-period SMA crossed below {slow_period}-period SMA (death cross)"
    return "hold", "no new crossover since the last check"


def _backdated(ts: datetime):
    """Monkeypatch storage._now for exactly one call so seeded rows carry a
    spread-out timestamp instead of "now" - makes the equity chart meaningful."""
    storage._now = lambda: ts.isoformat()  # noqa: SLF001 - intentional, demo-only


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Delete the existing database before seeding.")
    args = parser.parse_args()

    if args.reset:
        reset_db()

    seed()
    print(f"\nDemo data written to {storage.DB_PATH}")
    print("Run:  streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
