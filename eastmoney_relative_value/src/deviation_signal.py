from __future__ import annotations

import numpy as np
import pandas as pd


def deviation_level(value: float) -> str:
    if value > 0.05:
        return "明显偏贵"
    if value > 0.02:
        return "偏贵"
    if value >= -0.02:
        return "合理"
    if value >= -0.05:
        return "偏便宜"
    return "明显偏便宜"


def add_deviation_signals(df: pd.DataFrame, prediction: pd.Series) -> pd.DataFrame:
    out = df.copy()
    out["theoretical_return"] = prediction
    out["theoretical_price"] = out["close"].shift(1) * (1 + out["theoretical_return"])
    out["deviation_pct"] = out["close"] / out["theoretical_price"] - 1
    out["deviation_level"] = out["deviation_pct"].map(deviation_level)

    broker_ok = out["broker_trend20"] > -0.03
    amount_ok = out["amount_trend5"] > -0.08
    market_ok = out["market_trend20"] > -0.04
    volume_ok = out["stock_volume_change"] > -0.35
    out["buy_signal"] = (out["deviation_pct"] < -0.03) & broker_ok & amount_ok & market_ok
    out["strong_buy_signal"] = (out["deviation_pct"] < -0.05) & broker_ok & amount_ok & market_ok
    # 强板块/放量上涨时，正偏离先视为趋势而非简单高估。
    positive_trend = (out["broker_return"] > 0.01) & (out["market_amount_change"] > 0.05)
    out["sell_signal"] = (out["deviation_pct"] > 0.03) & ~positive_trend
    out["strong_sell_signal"] = (out["deviation_pct"] > 0.05) & ~positive_trend

    base_band = pd.concat(
        [
            (out["atr20"] / out["theoretical_price"]).clip(0.008, 0.08),
            (out["volatility20"] * 1.25).clip(0.008, 0.08),
        ],
        axis=1,
    ).max(axis=1).fillna(0.02)
    out["band_pct"] = base_band
    for idx, multiple in enumerate([0.75, 1.25, 1.75], start=1):
        out[f"buy_zone_{idx}"] = out["theoretical_price"] * (1 - base_band * multiple)
        out[f"sell_zone_{idx}"] = out["theoretical_price"] * (1 + base_band * multiple)
    volatility_stop = (2 * out["atr20"] / out["close"]).clip(0.03, 0.10).fillna(0.05)
    out["stop_loss_price"] = out["close"] * (1 - volatility_stop)
    risk_points = (
        (out["market_trend20"] < -0.04).astype(int)
        + (out["broker_trend20"] < -0.03).astype(int)
        + (out["volatility20"] > out["volatility20"].rolling(252, min_periods=60).quantile(0.8)).astype(int)
        + (out["amount_trend5"] < -0.08).astype(int)
    )
    out["risk_level"] = np.select([risk_points >= 3, risk_points >= 1], ["高", "中"], default="低")
    out["volume_filter_ok"] = volume_ok
    return out


def operation_advice(row: pd.Series) -> str:
    if row.get("risk_level") == "高":
        return "高风险环境，控制仓位并等待风险缓和"
    if row.get("strong_buy_signal", False):
        return "明显偏便宜，可重点观察并分批布局，严格止损"
    if row.get("buy_signal", False):
        return "偏便宜，可进入分批买入观察区"
    if row.get("strong_sell_signal", False):
        return "明显偏贵，可重点观察减仓或止盈"
    if row.get("sell_signal", False):
        return "偏贵，避免追涨，可考虑分批止盈"
    if row.get("deviation_level") == "偏贵":
        return "轻度偏贵但未达到卖出阈值，避免追涨并继续观察"
    if row.get("deviation_level") == "偏便宜":
        return "轻度偏便宜但过滤条件未满足，暂不急于买入"
    return "价格处于合理区间，观望为主"
