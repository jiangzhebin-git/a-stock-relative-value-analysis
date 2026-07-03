"""AkShare 数据获取与本地缓存。"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import INDEX_CODES
from .utils import save_csv

LOGGER = logging.getLogger(__name__)


def _normalize(df: pd.DataFrame, mapping: dict[str, str], required: list[str]) -> pd.DataFrame:
    out = df.rename(columns=mapping).copy()
    missing = [c for c in required if c not in out]
    if missing:
        raise ValueError(f"接口返回缺少字段: {missing}; 实际字段: {list(df.columns)}")
    out["date"] = pd.to_datetime(out["date"])
    for col in set(required) - {"date"}:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out[required].sort_values("date").drop_duplicates("date")


def _cached(path: Path, loader, force: bool) -> pd.DataFrame:
    def read_cache() -> pd.DataFrame:
        frame = pd.read_csv(path)
        for col in ["date", "datetime"]:
            if col in frame:
                frame[col] = pd.to_datetime(frame[col])
        return frame
    if path.exists() and not force:
        LOGGER.info("读取缓存 %s", path.name)
        return read_cache()
    try:
        frame = loader()
        save_csv(frame, path)
        return frame
    except Exception:
        if path.exists():
            LOGGER.exception("更新失败，降级读取缓存 %s", path.name)
            return read_cache()
        raise


def fetch_stock(ak, symbol: str, exchange: str, start: str, end: str) -> pd.DataFrame:
    try:
        raw = ak.stock_zh_a_hist(
            symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq"
        )
        mapping = {
            "日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
            "涨跌幅": "pct_change", "成交量": "volume", "成交额": "amount", "换手率": "turnover",
        }
    except Exception:
        LOGGER.warning("%s 东方财富行情接口不可用，改用 AkShare 新浪日线接口", symbol)
        try:
            raw = ak.stock_zh_a_daily(
                symbol=f"{exchange}{symbol}", start_date=start, end_date=end, adjust="qfq"
            )
            raw["pct_change"] = pd.to_numeric(raw["close"], errors="coerce").pct_change() * 100
            # 新浪接口换手率为小数，统一转成百分数口径。
            raw["turnover"] = pd.to_numeric(raw["turnover"], errors="coerce") * 100
            mapping = {}
        except Exception:
            LOGGER.warning("%s 新浪接口不可用，改用 AkShare 腾讯复权日线接口", symbol)
            raw = ak.stock_zh_a_hist_tx(
                symbol=f"{exchange}{symbol}", start_date=start, end_date=end,
                adjust="qfq", timeout=20,
            )
            # 腾讯接口的 amount 字段实际为成交量；金额和换手率只能构造代理。
            raw["volume"] = pd.to_numeric(raw["amount"], errors="coerce")
            raw["amount"] = raw["volume"] * pd.to_numeric(raw["close"], errors="coerce")
            raw["turnover"] = raw["volume"] / raw["volume"].rolling(60, min_periods=5).median() * 100
            raw["pct_change"] = pd.to_numeric(raw["close"], errors="coerce").pct_change() * 100
            mapping = {}
    cols = ["date", "open", "high", "low", "close", "pct_change", "volume", "amount", "turnover"]
    return _normalize(raw, mapping, cols)


def fetch_intraday(ak, symbol: str, exchange: str, start: str, end: str, period: str = "5") -> pd.DataFrame:
    """获取公开接口可提供的最长分钟线；不同接口的实际覆盖长度可能不同。"""
    try:
        raw = ak.stock_zh_a_hist_min_em(
            symbol=symbol,
            start_date=pd.to_datetime(start).strftime("%Y-%m-%d 09:30:00"),
            end_date=pd.to_datetime(end).strftime("%Y-%m-%d 15:00:00"),
            period=period,
            adjust="qfq",
        )
        mapping = {
            "时间": "datetime", "开盘": "open", "收盘": "close", "最高": "high",
            "最低": "low", "成交量": "volume", "成交额": "amount",
        }
        out = raw.rename(columns=mapping)
    except Exception:
        LOGGER.warning("%s 分钟主接口不可用，改用 AkShare 新浪近期分钟线", symbol)
        raw = ak.stock_zh_a_minute(symbol=f"{exchange}{symbol}", period=period, adjust="qfq")
        out = raw.rename(columns={"day": "datetime"})
    required = ["datetime", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in out]
    if missing:
        raise ValueError(f"{symbol} 分钟数据缺少字段 {missing}")
    if "amount" not in out:
        out["amount"] = pd.to_numeric(out["close"], errors="coerce") * pd.to_numeric(
            out["volume"], errors="coerce"
        )
    out["datetime"] = pd.to_datetime(out["datetime"])
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out[["datetime", "open", "high", "low", "close", "volume", "amount"]].dropna(
        subset=["datetime", "close"]
    ).sort_values("datetime").drop_duplicates("datetime")


def fetch_index(ak, code: str, start: str, end: str) -> pd.DataFrame:
    try:
        raw = ak.index_zh_a_hist(symbol=code, period="daily", start_date=start, end_date=end)
        mapping = {"日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
                   "成交量": "volume", "成交额": "amount"}
    except Exception:
        prefix = "sh" if code in {"000001", "000300"} else "sz"
        LOGGER.warning("东方财富指数接口 %s 不可用，改用 AkShare 新浪指数接口", code)
        raw = ak.stock_zh_index_daily(symbol=f"{prefix}{code}")
        raw["date"] = pd.to_datetime(raw["date"])
        raw = raw[(raw["date"] >= pd.to_datetime(start)) & (raw["date"] <= pd.to_datetime(end))]
        # 新浪指数日线无成交额；仅在备用通道中以收盘×成交量代理其变化率。
        raw["amount"] = pd.to_numeric(raw["close"]) * pd.to_numeric(raw["volume"])
        mapping = {}
    return _normalize(raw, mapping, ["date", "open", "high", "low", "close", "volume", "amount"])


def fetch_market_amount(ak, start: str, end: str) -> pd.DataFrame:
    frames = []
    for code, name in [("000001", "sh_amount"), ("399001", "sz_amount")]:
        frame = fetch_index(ak, code, start, end)[["date", "amount"]].rename(columns={"amount": name})
        frames.append(frame)
    result = frames[0].merge(frames[1], on="date", how="outer")
    result["market_amount"] = result["sh_amount"].fillna(0) + result["sz_amount"].fillna(0)
    return result.sort_values("date")


def fetch_market_data(data_dir: Path, start: str, end: str, force: bool = False) -> dict[str, pd.DataFrame]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("未安装 akshare，请先执行 pip install -r requirements.txt") from exc

    result = {}
    for feature, code in INDEX_CODES.items():
        result[feature] = _cached(
            data_dir / f"raw_index_{code}.csv", lambda c=code: fetch_index(ak, c, start, end), force
        )
    result["market_amount"] = _cached(
        data_dir / "raw_market_amount.csv", lambda: fetch_market_amount(ak, start, end), force
    )
    return result


def fetch_stock_data(
    data_dir: Path, symbol: str, exchange: str, start: str, end: str, force: bool = False,
    fetch_minutes: bool = True,
) -> dict[str, pd.DataFrame]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("未安装 akshare，请先执行 pip install -r requirements.txt") from exc
    result = {
        "stock": _cached(
            data_dir / f"raw_stock_{symbol}.csv",
            lambda: fetch_stock(ak, symbol, exchange, start, end),
            force,
        )
    }
    if fetch_minutes:
        try:
            result["intraday"] = _cached(
                data_dir / f"raw_intraday_{symbol}_5m.csv",
                lambda: fetch_intraday(ak, symbol, exchange, start, end, "5"),
                force,
            )
        except Exception:
            LOGGER.exception("%s 分钟线获取失败，日线分析继续", symbol)
            result["intraday"] = pd.DataFrame()
    return result


def fetch_all(data_dir: Path, start: str, end: str, force: bool = False) -> dict[str, pd.DataFrame]:
    """向后兼容原单股票入口。"""
    market = fetch_market_data(data_dir, start, end, force)
    stock = fetch_stock_data(data_dir, "300059", "sz", start, end, force, False)
    return {**market, **stock}
