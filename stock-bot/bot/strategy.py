"""Simple moving-average crossover trend strategy.

Signal logic (a "golden cross" / "death cross" system):
  - fast SMA crosses ABOVE slow SMA  -> BUY  (an uptrend may be starting)
  - fast SMA crosses BELOW slow SMA  -> SELL (an uptrend may be ending)
  - no crossover since the last check -> HOLD

This is one of the oldest, most transparent trend-following ideas there is -
deliberately so. It is easy to reason about and easy to watch fail, which
matters far more than squeezing out extra theoretical return when real money
is on the line. It will lag sharp moves and whipsaw in choppy/sideways
markets - that is expected, not a bug.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from .config import StrategyConfig


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TrendReading:
    symbol: str
    signal: Signal
    fast_sma: float
    slow_sma: float
    price: float
    reason: str


def evaluate(symbol: str, bars: pd.DataFrame, cfg: StrategyConfig) -> TrendReading | None:
    """Return the latest trend reading for `symbol`, or None if there isn't
    enough price history yet to compute both moving averages."""
    needed = cfg.slow_sma_period + 1  # +1 so we can detect a crossover
    if len(bars) < needed:
        return None

    closes = bars["close"]
    fast = closes.rolling(cfg.fast_sma_period).mean()
    slow = closes.rolling(cfg.slow_sma_period).mean()

    fast_now, fast_prev = fast.iloc[-1], fast.iloc[-2]
    slow_now, slow_prev = slow.iloc[-1], slow.iloc[-2]
    price = float(closes.iloc[-1])

    crossed_up = fast_prev <= slow_prev and fast_now > slow_now
    crossed_down = fast_prev >= slow_prev and fast_now < slow_now

    if crossed_up:
        signal, reason = Signal.BUY, (
            f"{cfg.fast_sma_period}-period SMA crossed above "
            f"{cfg.slow_sma_period}-period SMA (golden cross)"
        )
    elif crossed_down:
        signal, reason = Signal.SELL, (
            f"{cfg.fast_sma_period}-period SMA crossed below "
            f"{cfg.slow_sma_period}-period SMA (death cross)"
        )
    else:
        signal, reason = Signal.HOLD, "no new crossover since the last check"

    return TrendReading(
        symbol=symbol,
        signal=signal,
        fast_sma=float(fast_now),
        slow_sma=float(slow_now),
        price=price,
        reason=reason,
    )
