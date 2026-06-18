# Stock Bot

A trend-following trading bot (moving-average crossover), a SQLite activity
log, and a Streamlit dashboard to watch what it's doing — built on the
[Alpaca](https://alpaca.markets/) API.

## Read this before you do anything else

**This bot can lose real money if you run it in live mode.** Trend-following
is a simple, well-understood idea — and simple ideas routinely underperform or
lose money in real markets, especially for retail traders. Nothing here
"saves more money" or beats the market by design. What it *does* do is:

- trade transparently, on a rule you can read and understand (`bot/strategy.py`)
- enforce hard risk limits that the strategy cannot override (`bot/risk_manager.py`):
  **max position size**, **per-trade stop-loss**, and a **daily loss circuit
  breaker** that halts the bot (and can liquidate) once losses cross a line
- default to **paper trading** (simulated money, real market data) — you must
  deliberately edit config and type a confirmation phrase to go live

Treat any money you point this at as money you are fully prepared to lose.
Watch it run on paper for weeks, not minutes, before even considering live mode.

## Layout

```
stock-bot/
├── config.yaml           # mode (paper/live), watchlist, strategy params, risk limits
├── .env.example          # template for your Alpaca API keys (copy to .env)
├── run.py                # entry point - runs the trading loop
├── bot/
│   ├── config.py         # loads & validates config.yaml + .env
│   ├── broker.py         # all Alpaca API calls live here (paper or live)
│   ├── strategy.py       # SMA-crossover trend signal
│   ├── risk_manager.py   # hard position-size / stop-loss / circuit-breaker gates
│   ├── trader.py         # orchestrates one loop tick: data -> signal -> risk -> order
│   └── storage.py        # append-only SQLite log for the dashboard
├── dashboard/app.py      # Streamlit dashboard (read-only - cannot place trades)
└── data/bot.sqlite3      # local activity log (created on first run)
```

## Setup

1. **Create an Alpaca account** at https://alpaca.markets/ — it offers a free
   paper-trading sandbox with simulated money and real market data, using the
   exact same API as live trading.
2. **Get your paper API keys** from
   https://app.alpaca.markets/paper/dashboard/overview
3. ```bash
   cd stock-bot
   python -m venv .venv && source .venv/bin/activate   # or your preferred env tool
   pip install -r requirements.txt
   cp .env.example .env
   ```
4. Open `.env` and paste in `ALPACA_PAPER_API_KEY` / `ALPACA_PAPER_API_SECRET`.
   **Never commit `.env`** — it's already in `.gitignore`.
5. Review `config.yaml`. The defaults are conservative (small watchlist, 10%
   max position size, 5% stop-loss, 3% daily loss limit) — adjust only once
   you understand what each setting bounds.

## Running it

```bash
python run.py            # loops continuously, polling during market hours
python run.py --once     # runs a single tick and exits (good for testing / cron)
```

In a second terminal, start the dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard is **read-only** — it just displays `data/bot.sqlite3`, the log
the bot writes to. It cannot place or affect trades.

## How the strategy works

A classic moving-average crossover ("golden cross" / "death cross"):
- fast SMA crosses **above** the slow SMA → BUY signal (an uptrend may be starting)
- fast SMA crosses **below** the slow SMA → SELL signal (an uptrend may be ending)

It's deliberately simple and easy to audit. Expect it to lag sharp moves and
whipsaw (buy-then-immediately-sell) in sideways markets — that's normal
behaviour for any trend-follower, not a bug to "fix" by overfitting.

## How the risk gates work (read `bot/risk_manager.py`)

These are checked on **every** tick, regardless of what the strategy says:

1. **Daily loss circuit breaker** — if the account's equity has fallen by
   `daily_loss_limit_pct` from the day's opening equity, the bot stops opening
   new positions for the rest of the day (and liquidates everything, if
   `liquidate_on_circuit_breaker: true`).
2. **Stop-loss** — if an open position has fallen `stop_loss_pct` below its
   entry price, it is force-sold immediately, even if the trend strategy is
   currently saying "hold" or "buy more."
3. **Max position size** — a new BUY is sized so the position never exceeds
   `max_position_size_pct` of total account equity, and is skipped entirely if
   a position in that symbol already exists (no pyramiding into open trades).

## Going live (only after extended paper testing)

1. In `.env`, fill in `ALPACA_LIVE_API_KEY` / `ALPACA_LIVE_API_SECRET` from
   https://app.alpaca.markets/live/dashboard/overview
2. In `config.yaml`, change `paper: true` to `paper: false`.
3. On startup, you'll be asked to type an exact confirmation phrase
   acknowledging real financial risk — this is intentional friction, not a bug.

You can also set `I_UNDERSTAND_THIS_IS_LIVE_TRADING=yes` in the environment to
skip the interactive prompt for unattended/scheduled runs — only do this once
you have genuinely internalised what going live means.
