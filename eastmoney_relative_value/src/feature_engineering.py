import numpy as np
import pandas as pd

from .config import INDEX_CODES, MODEL_FEATURES


def _safe_change(series: pd.Series) -> pd.Series:
    return series.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)


def build_features(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy().sort_values("date").reset_index(drop=True)
    df["stock_return"] = _safe_change(df["close"])
    for feature in INDEX_CODES:
        df[feature] = _safe_change(df[feature.replace("_return", "_close")])
    df["market_amount_change"] = _safe_change(df["market_amount"])
    df["stock_volume_change"] = _safe_change(df["volume"])
    df["stock_turnover_change"] = _safe_change(df["turnover"])
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [(df["high"] - df["low"]), (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    df["atr20"] = tr.rolling(20, min_periods=10).mean()
    df["volatility20"] = df["stock_return"].rolling(20, min_periods=10).std()
    df["broker_trend20"] = df["broker_close"] / df["broker_close"].rolling(20).mean() - 1
    df["market_trend20"] = df["hs300_close"] / df["hs300_close"].rolling(20).mean() - 1
    df["amount_trend5"] = df["market_amount"] / df["market_amount"].rolling(5).mean() - 1
    change_cols = list(dict.fromkeys(sum(MODEL_FEATURES.values(), [])))
    for col in change_cols:
        lo, hi = df[col].quantile([0.005, 0.995])
        df[col] = df[col].clip(lo, hi)
    return df.dropna(subset=["stock_return"] + MODEL_FEATURES["D"]).reset_index(drop=True)

