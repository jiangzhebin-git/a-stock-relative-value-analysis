import pandas as pd

from notify_feishu import format_alerts, format_failure


def test_format_alerts_contains_core_fields():
    alerts = pd.DataFrame([{
        "date": "2026-07-02", "symbol": "300803", "name": "指南针",
        "title": "买入观察", "actual_price": 88.99, "theoretical_price": 92.0,
        "deviation_pct": -0.0327, "risk_level": "中", "advice": "分批观察",
    }])
    text = format_alerts(alerts)
    assert "指南针（300803）" in text
    assert "偏离：-3.27%" in text
    assert "不构成投资建议" in text


def test_empty_alerts_and_failure_message():
    assert format_alerts(pd.DataFrame()) == ""
    assert "运行失败" in format_failure("network timeout")

