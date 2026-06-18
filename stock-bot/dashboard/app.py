#!/usr/bin/env python3
"""Streamlit dashboard - read-only window into what the bot has seen and done.

Run with: streamlit run dashboard/app.py

This page never places trades or talks to the broker; it only reads the local
SQLite log that bot/storage.py writes to. That separation means you can have
the dashboard open all day without it being able to affect trading.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bot.sqlite3"

st.set_page_config(page_title="Stock Bot Dashboard", layout="wide")
st.title("📈 Stock Bot Dashboard")
st.caption(
    "Read-only view of the bot's account snapshots, trend readings, orders and "
    "events. This page cannot place trades — it only displays the local activity "
    "log written by run.py."
)


def load_table(name: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        try:
            df = pd.read_sql_query(f"SELECT * FROM {name} ORDER BY ts", conn)
        except pd.errors.DatabaseError:
            return pd.DataFrame()
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
    return df


snapshots = load_table("account_snapshots")
readings = load_table("trend_readings")
orders = load_table("orders")
events = load_table("events")

if snapshots.empty:
    st.info(
        "No data yet. Start the bot with `python run.py` (after configuring "
        "stock-bot/.env and config.yaml) and this dashboard will populate as it runs."
    )
    st.stop()

# -- Mode banner --------------------------------------------------------------

latest = snapshots.iloc[-1]
mode = latest["mode"]
if "LIVE" in mode:
    st.error(f"⚠️ Mode: {mode} — this bot is trading with REAL money.")
else:
    st.success(f"Mode: {mode} — simulated money, nothing real is at risk.")

# -- Account summary -----------------------------------------------------------

col1, col2, col3 = st.columns(3)
col1.metric("Equity", f"${latest['equity']:,.2f}")
col2.metric("Cash", f"${latest['cash']:,.2f}")
day_pl = latest["equity"] - latest["last_equity"]
day_pl_pct = (day_pl / latest["last_equity"]) if latest["last_equity"] else 0.0
col3.metric("Today's P&L", f"${day_pl:,.2f}", f"{day_pl_pct:.2%}")

st.subheader("Equity over time")
st.plotly_chart(
    px.line(snapshots, x="ts", y="equity", title=None),
    use_container_width=True,
)

# -- Trend readings -------------------------------------------------------------

st.subheader("Latest trend readings per symbol")
if not readings.empty:
    latest_per_symbol = readings.sort_values("ts").groupby("symbol").tail(1)
    st.dataframe(
        latest_per_symbol[["ts", "symbol", "signal", "price", "fast_sma", "slow_sma", "reason"]]
        .sort_values("symbol")
        .reset_index(drop=True),
        use_container_width=True,
    )

    symbol_choice = st.selectbox("Chart price vs. moving averages for:",
                                 sorted(readings["symbol"].unique()))
    sym_df = readings[readings["symbol"] == symbol_choice].sort_values("ts")
    chart_df = sym_df.melt(
        id_vars="ts", value_vars=["price", "fast_sma", "slow_sma"],
        var_name="series", value_name="value",
    )
    st.plotly_chart(
        px.line(chart_df, x="ts", y="value", color="series",
                title=f"{symbol_choice}: price vs. moving averages"),
        use_container_width=True,
    )
else:
    st.write("No trend readings logged yet.")

# -- Orders ----------------------------------------------------------------------

st.subheader("Order history")
if not orders.empty:
    st.dataframe(orders.sort_values("ts", ascending=False).reset_index(drop=True),
                 use_container_width=True)
else:
    st.write("No orders placed yet.")

# -- Events / log -----------------------------------------------------------------

st.subheader("Recent events")
if not events.empty:
    st.dataframe(events.sort_values("ts", ascending=False).head(200).reset_index(drop=True),
                 use_container_width=True)
else:
    st.write("No events logged yet.")
