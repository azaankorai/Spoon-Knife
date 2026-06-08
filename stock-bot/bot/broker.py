"""Thin wrapper around the Alpaca SDK for market data, account state and orders.

Centralising every Alpaca call here means: (a) paper vs. live is decided in
exactly one place, and (b) the rest of the bot only ever talks to this object,
so it's straightforward to point the strategy/risk logic at a fake broker in
tests without touching real APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .config import Config


@dataclass
class AccountState:
    equity: float
    cash: float
    last_equity: float  # equity at the most recent close - used for daily P&L


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    unrealized_pl: float


_TIMEFRAMES = {
    "1Day": TimeFrame.Day,
    "1Hour": TimeFrame.Hour,
    "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
    "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
    "1Min": TimeFrame.Minute,
}


class Broker:
    def __init__(self, config: Config):
        self.config = config
        self.trading_client = TradingClient(
            config.api_key, config.api_secret, paper=config.paper
        )
        # Market data is the same feed for paper and live accounts.
        self.data_client = StockHistoricalDataClient(config.api_key, config.api_secret)

    # -- Account / positions ------------------------------------------------

    def get_account(self) -> AccountState:
        acct = self.trading_client.get_account()
        return AccountState(
            equity=float(acct.equity),
            cash=float(acct.cash),
            last_equity=float(acct.last_equity),
        )

    def get_positions(self) -> dict[str, Position]:
        positions = self.trading_client.get_all_positions()
        return {
            p.symbol: Position(
                symbol=p.symbol,
                qty=float(p.qty),
                avg_entry_price=float(p.avg_entry_price),
                market_value=float(p.market_value),
                unrealized_pl=float(p.unrealized_pl),
            )
            for p in positions
        }

    def is_market_open(self) -> bool:
        return bool(self.trading_client.get_clock().is_open)

    # -- Market data ---------------------------------------------------------

    def get_price_history(self, symbol: str, days: int, timeframe: str) -> pd.DataFrame:
        tf = _TIMEFRAMES.get(timeframe, TimeFrame.Day)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=datetime.now(timezone.utc) - timedelta(days=days),
        )
        bars = self.data_client.get_stock_bars(request)
        df = bars.df
        if df.empty:
            return df
        # Multi-symbol responses are indexed by (symbol, timestamp); flatten to
        # a plain time-indexed frame for a single symbol.
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)
        return df.sort_index()

    def latest_price(self, symbol: str) -> float | None:
        df = self.get_price_history(symbol, days=5, timeframe="1Day")
        if df.empty:
            return None
        return float(df["close"].iloc[-1])

    # -- Orders ---------------------------------------------------------------

    def submit_market_order(self, symbol: str, qty: float, side: str) -> str:
        """Submit a market order. side is 'buy' or 'sell'. Returns the order id."""
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        request = MarketOrderRequest(
            symbol=symbol,
            qty=round(qty, 4),
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = self.trading_client.submit_order(order_data=request)
        return str(order.id)

    def liquidate_all(self) -> None:
        self.trading_client.close_all_positions(cancel_orders=True)
