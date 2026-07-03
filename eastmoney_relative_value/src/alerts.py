from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ALERT_LEVELS = {
    "明显偏便宜": ("strong_buy", "重点买入观察"),
    "偏便宜": ("buy_watch", "买入观察"),
    "偏贵": ("sell_watch", "卖出观察"),
    "明显偏贵": ("strong_sell", "重点卖出观察"),
}


def build_alerts(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in summary.itertuples(index=False):
        level = getattr(row, "deviation_level", "合理")
        if level not in ALERT_LEVELS:
            continue
        event_type, title = ALERT_LEVELS[level]
        # 普通信号必须通过模型过滤；明显偏离保留为重点观察事件。
        allowed = (
            level in {"明显偏便宜", "明显偏贵"}
            or bool(getattr(row, "buy_signal", False))
            or bool(getattr(row, "sell_signal", False))
        )
        if not allowed:
            continue
        rows.append({
            "event_id": f"{row.symbol}-{pd.Timestamp(row.date):%Y%m%d}-{event_type}",
            "date": row.date, "symbol": row.symbol, "name": row.name,
            "event_type": event_type, "title": title,
            "actual_price": row.actual_price, "theoretical_price": row.theoretical_price,
            "deviation_pct": row.deviation_pct, "risk_level": row.risk_level,
            "advice": row.advice,
        })
    return pd.DataFrame(rows)


def save_new_alerts(alerts: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    state_path = output_dir / "alert_state.json"
    seen = set()
    if state_path.exists():
        try:
            seen = set(json.loads(state_path.read_text(encoding="utf-8")).get("seen", []))
        except (json.JSONDecodeError, OSError):
            seen = set()
    new_alerts = alerts.loc[~alerts["event_id"].isin(seen)].copy() if not alerts.empty else alerts.copy()
    all_seen = sorted(seen | set(alerts.get("event_id", [])))
    state_path.write_text(json.dumps({"seen": all_seen[-1000:]}, ensure_ascii=False, indent=2), encoding="utf-8")
    alerts.to_csv(output_dir / "alerts.csv", index=False, encoding="utf-8-sig")
    (output_dir / "alerts.json").write_text(
        alerts.to_json(orient="records", force_ascii=False, date_format="iso", indent=2),
        encoding="utf-8",
    )
    new_alerts.to_csv(output_dir / "new_alerts.csv", index=False, encoding="utf-8-sig")
    return new_alerts

