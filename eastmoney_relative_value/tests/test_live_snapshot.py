from datetime import datetime

import pytest

from src.live_snapshot import build_live_snapshot, parse_tencent_quotes, trading_progress


def test_trading_progress_respects_lunch_break():
    assert trading_progress(datetime(2026, 7, 3, 9, 30)) == 0
    assert trading_progress(datetime(2026, 7, 3, 10, 30)) == pytest.approx(0.25)
    assert trading_progress(datetime(2026, 7, 3, 12, 0)) == 0.5
    assert trading_progress(datetime(2026, 7, 3, 14, 0)) == pytest.approx(0.75)
    assert trading_progress(datetime(2026, 7, 3, 15, 1)) == 1


def test_parse_quote_and_build_snapshot():
    fields = [""] * 80
    fields[1:7] = ["测试股", "300000", "10.50", "10.00", "10.10", "1200"]
    fields[30] = "20260703100000"
    fields[32:35] = ["5.00", "10.80", "9.90"]
    fields[35] = "10.50/1200/1260000"
    fields[38] = "1.20"
    text = f'v_sz300059="{"~".join(fields)}";'
    quote = parse_tencent_quotes(text)["sz300059"]
    assert quote["price"] == 10.5
    assert quote["amount"] == 1260000

    registry = {
        "generated_at": "2026-07-02T16:00:00+08:00", "data_date": "2026-07-02",
        "stocks": {
            "300059": {
                "name": "东方财富", "model": "A", "features": ["sh_return"],
                "intercept": 0.0, "coefficients": {"sh_return": 1.0},
                "base_close": 10.0, "previous_volume": 100000,
                "previous_turnover": 2.0, "previous_market_amount": 1e9,
                "band_pct": 0.02, "risk_level": "中", "data_date": "2026-07-02",
                "daily_fallback": {
                    "actual_price": 10.0, "theoretical_price": 10.0,
                    "deviation_pct": 0.0, "deviation_level": "合理",
                    "buy_zones": [9.8, 9.7, 9.6], "sell_zones": [10.2, 10.3, 10.4],
                    "stop_loss_price": 9.5,
                },
            }
        },
    }
    quotes = {
        "sz300059": quote,
        "sh000001": {**quote, "change_pct": 0.01},
    }
    snapshot = build_live_snapshot(registry, quotes, datetime(2026, 7, 3, 10, 30))
    assert snapshot["stocks"][0]["theoretical_price"] == pytest.approx(10.1)
    assert snapshot["stocks"][0]["mode"] == "dynamic_intraday"

