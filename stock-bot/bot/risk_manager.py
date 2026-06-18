"""Hard risk gates the strategy cannot override.

Nothing in this file tries to be clever or to improve returns - its only job
is to bound how much can go wrong. The strategy proposes; this module disposes.
If a proposed trade would breach a limit, it is shrunk or blocked outright,
and a circuit breaker can halt the bot for the rest of the day. Treat any
change to this file as something that directly changes how much money you can
lose - read it twice before editing it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .broker import AccountState, Position
from .config import RiskConfig


@dataclass
class SizedOrder:
    symbol: str
    qty: float
    side: str  # "buy" or "sell"
    reason: str


class CircuitBreakerTripped(Exception):
    """Raised when the daily loss limit is breached - the bot must stop opening
    new positions (and optionally liquidate) for the rest of the session."""


def check_circuit_breaker(account: AccountState, risk: RiskConfig) -> None:
    if account.last_equity <= 0:
        return
    daily_pl_pct = (account.equity - account.last_equity) / account.last_equity
    if daily_pl_pct <= -abs(risk.daily_loss_limit_pct):
        raise CircuitBreakerTripped(
            f"Daily loss {daily_pl_pct:.2%} breached the "
            f"{risk.daily_loss_limit_pct:.2%} limit "
            f"(equity {account.equity:.2f} vs. day-open {account.last_equity:.2f})"
        )


def size_buy_order(
    symbol: str,
    price: float,
    account: AccountState,
    existing_position: Position | None,
    risk: RiskConfig,
) -> SizedOrder | None:
    """Work out how large a BUY may be without breaching max_position_size_pct.

    Returns None if a position already exists (we don't pyramid into winners -
    that's how small losses become big ones) or if the allowed size rounds to
    zero shares.
    """
    if existing_position is not None:
        return None
    if price <= 0 or account.equity <= 0:
        return None

    max_position_value = account.equity * risk.max_position_size_pct
    affordable_value = min(max_position_value, account.cash)
    qty = affordable_value / price

    # Alpaca supports fractional shares; still avoid placing dust orders.
    if qty < 0.01:
        return None

    return SizedOrder(
        symbol=symbol,
        qty=qty,
        side="buy",
        reason=(
            f"sizing to {risk.max_position_size_pct:.0%} of equity "
            f"({affordable_value:.2f} / {price:.2f} = {qty:.4f} shares)"
        ),
    )


def stop_loss_order(
    symbol: str, position: Position, current_price: float, risk: RiskConfig
) -> SizedOrder | None:
    """If price has fallen stop_loss_pct below the entry, force a full exit -
    regardless of what the trend strategy currently says. The stop-loss always
    wins; trend signals do not get a vote on whether to cut a loss."""
    if position.avg_entry_price <= 0:
        return None
    drawdown = (current_price - position.avg_entry_price) / position.avg_entry_price
    if drawdown <= -abs(risk.stop_loss_pct):
        return SizedOrder(
            symbol=symbol,
            qty=abs(position.qty),
            side="sell",
            reason=(
                f"stop-loss triggered: price {current_price:.2f} is "
                f"{drawdown:.2%} below entry {position.avg_entry_price:.2f} "
                f"(limit {risk.stop_loss_pct:.0%})"
            ),
        )
    return None


def exit_order(symbol: str, position: Position, reason: str) -> SizedOrder:
    """A full exit driven by the strategy (e.g. a death-cross sell signal)."""
    return SizedOrder(symbol=symbol, qty=abs(position.qty), side="sell", reason=reason)
