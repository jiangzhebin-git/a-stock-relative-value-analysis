import pandas as pd

from .config import CORRELATION_FEATURES, LAGS


def lag_correlations(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in CORRELATION_FEATURES:
        for lag in LAGS:
            # feature(t-lag) 与 stock(t)：正 lag 表示解释变量领先东方财富。
            corr = df["stock_return"].corr(df[feature].shift(lag))
            rows.append({"variable": feature, "lag_days": lag, "correlation": corr})
    return pd.DataFrame(rows)

