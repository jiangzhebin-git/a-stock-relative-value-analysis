import logging
from pathlib import Path

import pandas as pd

from .config import INDEX_CODES
from .utils import save_csv

LOGGER = logging.getLogger(__name__)


def merge_market_data(raw: dict[str, pd.DataFrame], data_dir: Path | None = None) -> pd.DataFrame:
    stock = raw["stock"].copy().sort_values("date")
    stock["date"] = pd.to_datetime(stock["date"])
    merged = stock
    for feature in INDEX_CODES:
        idx = raw[feature][["date", "close"]].copy()
        idx["date"] = pd.to_datetime(idx["date"])
        merged = merged.merge(idx.rename(columns={"close": feature.replace("_return", "_close")}),
                              on="date", how="inner")
    amount = raw["market_amount"][["date", "market_amount"]].copy()
    amount["date"] = pd.to_datetime(amount["date"])
    merged = merged.merge(amount, on="date", how="inner")
    merged = merged.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if merged.empty:
        raise ValueError("不同数据源按日期对齐后为空，请检查数据区间与接口结果")
    if data_dir:
        save_csv(merged, data_dir / "clean_merged.csv")
    LOGGER.info("清洗合并完成：%d 行，%s 至 %s", len(merged), merged.date.min().date(), merged.date.max().date())
    return merged

