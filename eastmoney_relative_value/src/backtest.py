from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import annualized_return, finite_or


def run_backtest(df: pd.DataFrame, model: str = "") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    data = df.copy().reset_index(drop=True)
    cash, shares, entry_price, entry_date, entry_value = 1.0, 0.0, np.nan, None, np.nan
    pending_buy = pending_sell = False
    equity_rows, trades = [], []

    for i, row in data.iterrows():
        price = float(row["open"]) if np.isfinite(row["open"]) and row["open"] > 0 else float(row["close"])
        if pending_sell and shares > 0:
            proceeds = shares * price
            pnl = proceeds / entry_value - 1
            trades.append({
                "model": model, "entry_date": entry_date, "exit_date": row["date"],
                "entry_price": entry_price, "exit_price": price, "return": pnl,
                "holding_days": (pd.Timestamp(row["date"]) - pd.Timestamp(entry_date)).days,
            })
            cash, shares = proceeds, 0.0
            pending_sell = False
        if pending_buy and shares == 0:
            entry_value = cash
            shares, cash = cash / price, 0.0
            entry_price, entry_date = price, row["date"]
            pending_buy = False

        close_equity = cash + shares * float(row["close"])
        equity_rows.append({"date": row["date"], "equity": close_equity, "position": int(shares > 0)})

        if shares > 0:
            pnl_close = float(row["close"]) / entry_price - 1
            weakened = row.get("broker_trend20", 0) < -0.05
            exit_now = (
                bool(row.get("sell_signal", False))
                or abs(row.get("deviation_pct", 1)) < 0.005
                or pnl_close >= 0.08
                or pnl_close <= -0.05
                or weakened
                or row.get("deviation_pct", 0) < -0.09
            )
            pending_sell = bool(exit_now)
        elif bool(row.get("buy_signal", False)):
            pending_buy = True

    if shares > 0:
        last = data.iloc[-1]
        proceeds = shares * float(last["close"])
        trades.append({
            "model": model, "entry_date": entry_date, "exit_date": last["date"],
            "entry_price": entry_price, "exit_price": float(last["close"]),
            "return": proceeds / entry_value - 1,
            "holding_days": (pd.Timestamp(last["date"]) - pd.Timestamp(entry_date)).days,
        })
        equity_rows[-1]["equity"] = proceeds

    equity = pd.DataFrame(equity_rows)
    equity["return"] = equity["equity"].pct_change(fill_method=None).fillna(0)
    equity["drawdown"] = equity["equity"] / equity["equity"].cummax() - 1
    trades_df = pd.DataFrame(trades)
    total_return = finite_or(equity["equity"].iloc[-1] - 1 if not equity.empty else 0)
    wins = trades_df.loc[trades_df.get("return", pd.Series(dtype=float)) > 0, "return"] if not trades_df.empty else pd.Series(dtype=float)
    losses = trades_df.loc[trades_df.get("return", pd.Series(dtype=float)) <= 0, "return"] if not trades_df.empty else pd.Series(dtype=float)
    gross_profit, gross_loss = wins.sum(), abs(losses.sum())
    metrics = {
        "model": model,
        "total_return": total_return,
        "annualized_return": annualized_return(total_return, len(equity)),
        "max_drawdown": finite_or(equity["drawdown"].min() if not equity.empty else 0),
        "trade_count": int(len(trades_df)),
        "win_rate": finite_or((trades_df["return"] > 0).mean() if not trades_df.empty else 0),
        "profit_loss_ratio": finite_or(wins.mean() / abs(losses.mean()) if len(losses) and len(wins) else 0),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (np.inf if gross_profit > 0 else 0),
        "avg_holding_days": finite_or(trades_df["holding_days"].mean() if not trades_df.empty else 0),
    }
    return equity, trades_df, metrics


def benchmark_metrics(df: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    base = df.loc[df["date"].isin(equity["date"])].copy()
    base["stock_buy_hold"] = base["close"] / base["close"].iloc[0]
    base["hs300_buy_hold"] = base["hs300_close"] / base["hs300_close"].iloc[0]
    return equity.merge(base[["date", "stock_buy_hold", "hs300_buy_hold"]], on="date", how="left")

