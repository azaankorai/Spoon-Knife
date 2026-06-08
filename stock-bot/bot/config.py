"""Loads and validates config.yaml plus API credentials from the environment."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class StrategyConfig:
    fast_sma_period: int
    slow_sma_period: int
    bar_timeframe: str
    lookback_days: int


@dataclass(frozen=True)
class RiskConfig:
    max_position_size_pct: float
    stop_loss_pct: float
    daily_loss_limit_pct: float
    liquidate_on_circuit_breaker: bool


@dataclass(frozen=True)
class Config:
    paper: bool
    watchlist: list[str]
    poll_interval_seconds: int
    strategy: StrategyConfig
    risk: RiskConfig
    api_key: str
    api_secret: str

    @property
    def mode_label(self) -> str:
        return "PAPER (simulated money)" if self.paper else "LIVE (REAL MONEY)"


def load_config(path: Path | None = None) -> Config:
    path = path or (ROOT / "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    trading = raw["trading"]
    strategy = raw["strategy"]
    risk = raw["risk"]
    paper = bool(trading["paper"])

    # Separate key pairs for paper vs. live keep you from ever live-trading by
    # accident with paper credentials (Alpaca issues different keys for each).
    prefix = "ALPACA_PAPER" if paper else "ALPACA_LIVE"
    api_key = os.environ.get(f"{prefix}_API_KEY", "")
    api_secret = os.environ.get(f"{prefix}_API_SECRET", "")
    if not api_key or not api_secret:
        raise RuntimeError(
            f"Missing {prefix}_API_KEY / {prefix}_API_SECRET. Set them in "
            f"stock-bot/.env (see .env.example) before running in "
            f"{'paper' if paper else 'LIVE'} mode."
        )

    if not paper:
        _confirm_live_trading()

    return Config(
        paper=paper,
        watchlist=[s.upper() for s in trading["watchlist"]],
        poll_interval_seconds=int(trading["poll_interval_seconds"]),
        strategy=StrategyConfig(
            fast_sma_period=int(strategy["fast_sma_period"]),
            slow_sma_period=int(strategy["slow_sma_period"]),
            bar_timeframe=str(strategy["bar_timeframe"]),
            lookback_days=int(strategy["lookback_days"]),
        ),
        risk=RiskConfig(
            max_position_size_pct=float(risk["max_position_size_pct"]),
            stop_loss_pct=float(risk["stop_loss_pct"]),
            daily_loss_limit_pct=float(risk["daily_loss_limit_pct"]),
            liquidate_on_circuit_breaker=bool(risk["liquidate_on_circuit_breaker"]),
        ),
        api_key=api_key,
        api_secret=api_secret,
    )


def _confirm_live_trading() -> None:
    """Require an explicit, typed confirmation before any live run starts.

    config.yaml alone is not enough to arm live trading - a stray edit or a
    copy-pasted config shouldn't be able to put real money at risk silently.
    """
    if os.environ.get("I_UNDERSTAND_THIS_IS_LIVE_TRADING") == "yes":
        return
    print(
        "\n*** LIVE TRADING MODE ***\n"
        "config.yaml has paper: false. This bot will place REAL orders with "
        "REAL money using your live Alpaca account.\n"
        "Type the exact phrase below to continue, or anything else to abort.\n"
    )
    answer = input("Type 'I accept the risk of real financial loss': ").strip()
    if answer != "I accept the risk of real financial loss":
        raise SystemExit("Live trading not confirmed - aborting.")
