import pandas as pd

from .config import CORRELATION_FEATURES


def correlation_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["stock_return"] + CORRELATION_FEATURES
    return df[cols].corr()


def correlation_summary(df: pd.DataFrame) -> pd.DataFrame:
    values = df[CORRELATION_FEATURES].corrwith(df["stock_return"])
    result = values.rename("same_day_correlation").sort_values(ascending=False).reset_index()
    return result.rename(columns={"index": "variable"})
