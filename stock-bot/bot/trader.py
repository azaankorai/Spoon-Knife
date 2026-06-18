"""Orchestrates one trading-loop tick: data -> trend signal -> risk gate -> order.

The order of operations matters and is intentional:
  1. Refresh account state and check the circuit breaker FIRST. If it's
     tripped, no new positions are opened this session, full stop.
  2. For each symbol: check the stop-loss before the trend signal. A stop-loss
     exit always overrides a "hold"/"buy" reading from the strategy - cutting
     a loss is never something we let the trend model talk us out of.
  3. Only after both of those gates pass does a strategy-driven signal get to
     place an order, and even then it's sized by the risk manager, never by
     the strategy itself.
"""
from __future__ import annotations

from . import storage
from .broker import Broker
from .config import Config
from .risk_manager import (
    CircuitBreakerTripped,
    check_circuit_breaker,
    exit_order,
    size_buy_order,
    stop_loss_order,
)
from .strategy import Signal, evaluate


class Trader:
    def __init__(self, config: Config, broker: Broker):
        self.config = config
        self.broker = broker
        self._circuit_breaker_tripped_today = False

    def run_once(self) -> None:
        """Execute a single tick of the trading loop. Safe to call repeatedly -
        all state (positions, equity, day-open equity) is read fresh from the
        broker each time rather than tracked locally, so a restart can't drift
        out of sync with reality."""
        account = self.broker.get_account()
        storage.log_account_snapshot(
            mode=self.config.mode_label,
            equity=account.equity,
            cash=account.cash,
            last_equity=account.last_equity,
        )

        try:
            check_circuit_breaker(account, self.config.risk)
            if self._circuit_breaker_tripped_today:
                storage.log_event(
                    "info", "Circuit breaker previously tripped today; staying halted."
                )
                return
        except CircuitBreakerTripped as exc:
            self._handle_circuit_breaker(exc)
            return

        positions = self.broker.get_positions()

        for symbol in self.config.watchlist:
            self._process_symbol(symbol, account, positions)

    # -- per-symbol handling --------------------------------------------------

    def _process_symbol(self, symbol, account, positions) -> None:
        position = positions.get(symbol)
        price = self.broker.latest_price(symbol)
        if price is None:
            storage.log_event("warning", f"{symbol}: no recent price data, skipping.")
            return

        # Stop-loss is checked first and unconditionally - it overrides
        # whatever the trend strategy currently thinks.
        if position is not None:
            forced_exit = stop_loss_order(symbol, position, price, self.config.risk)
            if forced_exit is not None:
                self._place(forced_exit)
                return

        bars = self.broker.get_price_history(
            symbol,
            days=self.config.strategy.lookback_days,
            timeframe=self.config.strategy.bar_timeframe,
        )
        reading = evaluate(symbol, bars, self.config.strategy)
        if reading is None:
            storage.log_event(
                "info", f"{symbol}: not enough price history yet to compute trend."
            )
            return

        storage.log_trend_reading(
            symbol=reading.symbol,
            signal=reading.signal.value,
            price=reading.price,
            fast_sma=reading.fast_sma,
            slow_sma=reading.slow_sma,
            reason=reading.reason,
        )

        if reading.signal is Signal.BUY:
            order = size_buy_order(symbol, price, account, position, self.config.risk)
            if order is not None:
                self._place(order)
        elif reading.signal is Signal.SELL and position is not None:
            self._place(exit_order(symbol, position, reading.reason))
        # HOLD, or a signal with no actionable position change -> nothing to do.

    # -- circuit breaker -------------------------------------------------------

    def _handle_circuit_breaker(self, exc: CircuitBreakerTripped) -> None:
        self._circuit_breaker_tripped_today = True
        storage.log_event("critical", f"CIRCUIT BREAKER TRIPPED: {exc}")
        if self.config.risk.liquidate_on_circuit_breaker:
            storage.log_event("critical", "Liquidating all positions per config.")
            try:
                self.broker.liquidate_all()
                storage.log_order(
                    symbol="ALL", side="sell", qty=0, order_id=None,
                    reason="circuit breaker liquidation", status="submitted",
                )
            except Exception as e:  # pragma: no cover - defensive logging only
                storage.log_event("critical", f"Liquidation request failed: {e}")
        else:
            storage.log_event(
                "warning",
                "liquidate_on_circuit_breaker is false - existing positions are "
                "left open, but no new positions will be opened for the rest of "
                "the day.",
            )

    # -- order placement -------------------------------------------------------

    def _place(self, order) -> None:
        try:
            order_id = self.broker.submit_market_order(order.symbol, order.qty, order.side)
            storage.log_order(
                symbol=order.symbol, side=order.side, qty=order.qty,
                order_id=order_id, reason=order.reason, status="submitted",
            )
            storage.log_event(
                "info",
                f"{order.side.upper()} {order.qty:.4f} {order.symbol} "
                f"submitted ({order_id}) - {order.reason}",
            )
        except Exception as e:
            storage.log_order(
                symbol=order.symbol, side=order.side, qty=order.qty,
                order_id=None, reason=order.reason, status=f"failed: {e}",
            )
            storage.log_event(
                "error", f"Order failed for {order.symbol} {order.side}: {e}"
            )
