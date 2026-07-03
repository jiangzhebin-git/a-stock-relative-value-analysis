import numpy as np
import pandas as pd

from src.backtest import run_backtest
from src.alerts import build_alerts
from src.config import INDEX_CODES, STOCKS
from src.correlation_analysis import correlation_summary
from src.deviation_signal import add_deviation_signals, deviation_level
from src.feature_engineering import build_features
from src.intraday_analysis import analyze_intraday
from src.model_compare import compare_models


def synthetic_data(n=700, seed=7):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    market = rng.normal(0.0002, 0.012, n)
    broker = 1.3 * market + rng.normal(0, 0.01, n)
    stock_ret = 0.25 * market + 0.55 * broker + rng.normal(0, 0.012, n)
    close = 12 * np.cumprod(1 + stock_ret)
    frame = pd.DataFrame({
        "date": dates, "open": close * (1 + rng.normal(0, .003, n)),
        "high": close * 1.015, "low": close * .985, "close": close,
        "pct_change": stock_ret * 100, "volume": 1e6 * np.exp(rng.normal(0, .2, n)),
        "amount": close * 1e6, "turnover": 2 + rng.normal(0, .2, n),
        "market_amount": 8e11 * np.exp(np.cumsum(rng.normal(0, .03, n))),
    })
    for feature in INDEX_CODES:
        ret = broker if feature == "broker_return" else market + rng.normal(0, .003, n)
        frame[feature.replace("_return", "_close")] = 1000 * np.cumprod(1 + ret)
    return frame


def test_deviation_boundaries():
    assert deviation_level(.06) == "明显偏贵"
    assert deviation_level(.03) == "偏贵"
    assert deviation_level(0) == "合理"
    assert deviation_level(-.03) == "偏便宜"
    assert deviation_level(-.06) == "明显偏便宜"


def test_models_signals_and_backtest_are_finite():
    features = build_features(synthetic_data())
    summary = correlation_summary(features)
    assert {"variable", "same_day_correlation"} <= set(summary.columns)
    metrics, predictions, coefficients = compare_models(features)
    assert set(metrics.model) == {"A", "B", "C", "D"}
    assert metrics[["r2", "mae", "rmse", "direction_accuracy"]].notna().all().all()
    assert not coefficients.empty
    signals = add_deviation_signals(features, predictions["pred_D"])
    valid = signals.dropna(subset=["theoretical_price"]).reset_index(drop=True)
    assert np.allclose(
        valid["deviation_pct"], valid["close"] / valid["theoretical_price"] - 1
    )
    assert (valid["buy_zone_1"] < valid["theoretical_price"]).all()
    assert (valid["sell_zone_1"] > valid["theoretical_price"]).all()
    equity, trades, result = run_backtest(valid, "D")
    assert np.isfinite(equity["equity"]).all()
    assert result["trade_count"] == len(trades)
    assert -1 <= result["max_drawdown"] <= 0


def test_stock_pool_intraday_and_alerts():
    assert set(STOCKS) == {"300059", "300033", "300803", "688318"}
    features = build_features(synthetic_data())
    _, predictions, _ = compare_models(features)
    signals = add_deviation_signals(features, predictions["pred_B"]).dropna(
        subset=["theoretical_price"]
    )
    minutes = pd.DataFrame({
        "datetime": pd.date_range("2026-07-02 09:30", periods=3, freq="5min"),
        "open": [20, 20.1, 20.2], "high": [20.2, 20.3, 20.4],
        "low": [19.9, 20, 20.1], "close": [20, 20.2, 20.3],
        "volume": [100, 120, 150], "amount": [2000, 2424, 3045],
    })
    result = analyze_intraday(minutes, signals, "300033", "同花顺")
    assert {"theoretical_center", "deviation_pct", "price_zone"} <= set(result.columns)
    summary = pd.DataFrame([{
        "date": "2026-07-02", "symbol": "300033", "name": "同花顺",
        "deviation_level": "明显偏贵", "buy_signal": False, "sell_signal": False,
        "actual_price": 20.3, "theoretical_price": 18, "deviation_pct": .128,
        "risk_level": "中", "advice": "重点观察",
    }])
    alerts = build_alerts(summary)
    assert alerts.iloc[0]["event_type"] == "strong_sell"
