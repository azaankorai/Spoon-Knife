#!/usr/bin/env python3
"""Entry point for the trading bot's main loop.

Usage:
    python run.py            # run continuously, polling at the configured interval
    python run.py --once     # run a single tick and exit (good for cron / testing)

Always starts in whatever mode config.yaml says (paper by default). Live mode
requires both the ALPACA_LIVE_* keys in .env AND a typed confirmation at
startup - see bot/config.py.
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from bot import storage
from bot.broker import Broker
from bot.config import load_config
from bot.trader import Trader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single tick and exit, instead of looping continuously.",
    )
    args = parser.parse_args()

    config = load_config()
    broker = Broker(config)
    trader = Trader(config, broker)

    storage.log_event(
        "info",
        f"Starting in {config.mode_label} mode | watchlist={config.watchlist} | "
        f"max_position={config.risk.max_position_size_pct:.0%} "
        f"stop_loss={config.risk.stop_loss_pct:.0%} "
        f"daily_loss_limit={config.risk.daily_loss_limit_pct:.0%}",
    )

    if args.once:
        _tick(trader, broker)
        return

    while True:
        if broker.is_market_open():
            _tick(trader, broker)
        else:
            print(f"[{datetime.now(timezone.utc).isoformat()}] Market closed - waiting.")
        time.sleep(config.poll_interval_seconds)


def _tick(trader: Trader, broker: Broker) -> None:
    try:
        trader.run_once()
    except Exception as e:
        # A crashed loop iteration must never silently stop risk monitoring -
        # log it loudly and let the outer loop retry on the next interval.
        storage.log_event("error", f"Trading loop tick failed: {e}")


if __name__ == "__main__":
    main()
