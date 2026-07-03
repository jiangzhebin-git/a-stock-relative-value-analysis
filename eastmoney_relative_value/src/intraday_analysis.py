from __future__ import annotations

import numpy as np
import pandas as pd


def analyze_intraday(
    intraday: pd.DataFrame, daily_signal: pd.DataFrame, symbol: str, name: str
) -> pd.DataFrame:
    if intraday.empty or daily_signal.empty:
        return pd.DataFrame()
    latest = daily_signal.dropna(subset=["theoretical_price"]).iloc[-1]
    out = intraday.copy()
    out["symbol"] = symbol
    out["name"] = name
    out["theoretical_center"] = float(latest["theoretical_price"])
    out["deviation_pct"] = out["close"] / out["theoretical_center"] - 1
    thresholds = [
        out["close"] <= float(latest["buy_zone_3"]),
        out["close"] <= float(latest["buy_zone_2"]),
        out["close"] <= float(latest["buy_zone_1"]),
        out["close"] >= float(latest["sell_zone_3"]),
        out["close"] >= float(latest["sell_zone_2"]),
        out["close"] >= float(latest["sell_zone_1"]),
    ]
    choices = ["买入三区", "买入二区", "买入一区", "卖出三区", "卖出二区", "卖出一区"]
    out["price_zone"] = np.select(thresholds, choices, default="中性区")
    out["reference_daily_date"] = pd.Timestamp(latest["date"])
    out["risk_level"] = latest["risk_level"]
    return out


def intraday_summary(intraday_result: pd.DataFrame) -> dict:
    if intraday_result.empty:
        return {
            "intraday_start": pd.NaT, "intraday_end": pd.NaT, "intraday_rows": 0,
            "intraday_price": np.nan, "intraday_zone": "无分钟数据",
        }
    row = intraday_result.iloc[-1]
    return {
        "intraday_start": intraday_result["datetime"].min(),
        "intraday_end": intraday_result["datetime"].max(),
        "intraday_rows": len(intraday_result),
        "intraday_price": row["close"],
        "intraday_zone": row["price_zone"],
    }

