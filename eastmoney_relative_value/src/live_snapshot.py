from __future__ import annotations

import json
import re
from datetime import datetime, time
from pathlib import Path

import numpy as np
import requests

from .config import INDEX_CODES
from .deviation_signal import deviation_level

QUOTE_CODES = {
    "300059": "sz300059", "300033": "sz300033",
    "300803": "sz300803", "688318": "sh688318",
    "sh_return": "sh000001", "sz_return": "sz399001",
    "cyb_return": "sz399006", "hs300_return": "sh000300",
    "broker_return": "sz399975",
}


def trading_progress(at: datetime) -> float:
    """A股已完成交易分钟占全天240分钟的比例。"""
    current = at.time()
    if current < time(9, 30):
        return 0.0
    if current <= time(11, 30):
        minutes = (at.hour * 60 + at.minute) - (9 * 60 + 30)
        return min(max(minutes / 240, 0.0), 0.5)
    if current < time(13, 0):
        return 0.5
    if current <= time(15, 0):
        minutes = 120 + (at.hour * 60 + at.minute) - 13 * 60
        return min(max(minutes / 240, 0.5), 1.0)
    return 1.0


def parse_tencent_quotes(text: str) -> dict[str, dict]:
    quotes = {}
    for code, body in re.findall(r'v_([^=]+)="([^"]*)"', text):
        fields = body.split("~")
        if len(fields) < 39 or not fields[3]:
            continue
        timestamp = fields[30] if len(fields) > 30 else ""
        traded = fields[35].split("/") if len(fields) > 35 else []
        quotes[code] = {
            "price": float(fields[3]), "previous_close": float(fields[4]),
            "open": float(fields[5] or 0), "volume": float(fields[6] or 0) * 100,
            "change_pct": float(fields[32] or 0) / 100,
            "high": float(fields[33] or 0), "low": float(fields[34] or 0),
            "amount": float(traded[2]) if len(traded) >= 3 and traded[2] else 0.0,
            "turnover": float(fields[38] or 0),
            "timestamp": datetime.strptime(timestamp, "%Y%m%d%H%M%S") if timestamp else None,
        }
    return quotes


def fetch_tencent_quotes(timeout: int = 15) -> dict[str, dict]:
    codes = ",".join(QUOTE_CODES.values())
    response = requests.get(f"https://qt.gtimg.cn/q={codes}", timeout=timeout)
    response.raise_for_status()
    response.encoding = "gbk"
    return parse_tencent_quotes(response.text)


def _zones(center: float, band: float) -> tuple[list[float], list[float]]:
    buy = [center * (1 - band * m) for m in (0.75, 1.25, 1.75)]
    sell = [center * (1 + band * m) for m in (0.75, 1.25, 1.75)]
    return buy, sell


def build_live_snapshot(registry: dict, quotes: dict[str, dict], generated_at: datetime) -> dict:
    progress = max(trading_progress(generated_at), 0.08)
    index_features = {
        feature: quotes[QUOTE_CODES[feature]]["change_pct"]
        for feature in INDEX_CODES
        if QUOTE_CODES[feature] in quotes
    }
    market_amount = sum(
        quotes.get(code, {}).get("amount", 0.0) for code in ("sh000001", "sz399001")
    )
    stocks = []
    for symbol, model in registry["stocks"].items():
        quote = quotes.get(QUOTE_CODES[symbol])
        fallback = model["daily_fallback"]
        if not quote:
            stocks.append({
                "symbol": symbol, "name": model["name"], **fallback,
                "mode": "static_fallback", "confidence": "低",
                "data_time": model["data_date"], "message": "实时行情不可用，显示最近日线结果",
            })
            continue
        features = dict(index_features)
        estimated_market_amount = market_amount / progress if market_amount else 0.0
        features["market_amount_change"] = (
            estimated_market_amount / model["previous_market_amount"] - 1
            if estimated_market_amount and model["previous_market_amount"] else 0.0
        )
        estimated_volume = quote["volume"] / progress
        features["stock_volume_change"] = (
            estimated_volume / model["previous_volume"] - 1
            if model["previous_volume"] else 0.0
        )
        estimated_turnover = quote["turnover"] / progress
        features["stock_turnover_change"] = (
            estimated_turnover / model["previous_turnover"] - 1
            if model["previous_turnover"] else 0.0
        )
        theoretical_return = model["intercept"] + sum(
            model["coefficients"].get(feature, 0.0) * features.get(feature, 0.0)
            for feature in model["features"]
        )
        theoretical_return = float(np.clip(theoretical_return, -0.20, 0.20))
        theoretical_price = model["base_close"] * (1 + theoretical_return)
        deviation = quote["price"] / theoretical_price - 1
        buy, sell = _zones(theoretical_price, model["band_pct"])
        missing = [f for f in model["features"] if f not in features]
        confidence = "高" if not missing and progress >= 0.25 else "中"
        stocks.append({
            "symbol": symbol, "name": model["name"], "model": model["model"],
            "actual_price": quote["price"], "theoretical_price": theoretical_price,
            "deviation_pct": deviation, "deviation_level": deviation_level(deviation),
            "buy_zones": buy, "sell_zones": sell,
            "stop_loss_price": fallback["stop_loss_price"],
            "risk_level": model["risk_level"], "mode": "dynamic_intraday",
            "confidence": confidence,
            "data_time": quote["timestamp"].isoformat() if quote["timestamp"] else generated_at.isoformat(),
            "market_progress": progress, "missing_features": missing,
            "message": "累计量能已按当前交易时间折算为预计全天值",
        })
    return {
        "schema_version": 1, "generated_at": generated_at.isoformat(),
        "model_generated_at": registry["generated_at"],
        "model_data_date": registry["data_date"],
        "stocks": stocks,
    }


def update_snapshot(registry_path: Path, output_path: Path) -> dict:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    now = datetime.now().astimezone()
    try:
        snapshot = build_live_snapshot(registry, fetch_tencent_quotes(), now)
    except Exception as exc:
        snapshot = build_live_snapshot(registry, {}, now)
        snapshot["error"] = str(exc)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot

