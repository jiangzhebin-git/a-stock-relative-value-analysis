from __future__ import annotations

import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.alerts import build_alerts, save_new_alerts
from src.backtest import benchmark_metrics, run_backtest
from src.config import MODEL_FEATURES, RISK_WARNING, STOCKS, ensure_dirs
from src.correlation_analysis import correlation_summary, correlation_table
from src.deviation_signal import add_deviation_signals, operation_advice
from src.feature_engineering import build_features
from src.fetch_data import fetch_market_data, fetch_stock_data
from src.intraday_analysis import analyze_intraday, intraday_summary
from src.lag_analysis import lag_correlations
from src.model_compare import compare_models, select_best_model
from src.preprocess import merge_market_data
from src.report import create_report
from src.utils import save_csv, setup_logging
from src.visualize import create_charts

LOGGER = logging.getLogger("relative_value")


def run_single_stock(
    root: Path, symbol: str, metadata: dict, market: dict[str, pd.DataFrame],
    start: str, end: str, force: bool, fetch_minutes: bool,
) -> dict:
    name, exchange = metadata["name"], metadata["exchange"]
    stock_data_dir = root / "data" / symbol
    stock_output_dir = root / "output" / symbol
    stock_data_dir.mkdir(parents=True, exist_ok=True)
    stock_output_dir.mkdir(parents=True, exist_ok=True)
    requested_start = max(pd.Timestamp(start), pd.Timestamp(metadata["listed"])).strftime("%Y%m%d")
    stock_raw = fetch_stock_data(
        stock_data_dir, symbol, exchange, requested_start, end.replace("-", ""), force, fetch_minutes
    )
    raw = {**market, "stock": stock_raw["stock"]}
    merged = merge_market_data(raw, stock_data_dir)
    features = build_features(merged)
    save_csv(features, stock_data_dir / "features.csv")

    corr = correlation_table(features)
    corr_sum = correlation_summary(features)
    lag = lag_correlations(features)
    save_csv(corr.reset_index(names="variable"), stock_output_dir / "correlation_matrix.csv")
    save_csv(corr_sum, stock_output_dir / "correlation_summary.csv")
    save_csv(lag, stock_output_dir / "lag_correlations.csv")

    model_metrics, predictions, coefficients = compare_models(features)
    all_bt_metrics, payloads = [], {}
    for model in model_metrics["model"]:
        signals = add_deviation_signals(features, predictions[f"pred_{model}"])
        valid = signals.dropna(subset=["theoretical_price"]).reset_index(drop=True)
        equity, trades, metrics = run_backtest(valid, model)
        future_5d_return = valid["close"].shift(-5) / valid["close"] - 1
        metrics["signal_win_rate"] = (
            float(future_5d_return[valid.buy_signal].gt(0).mean()) if valid.buy_signal.any() else 0.0
        )
        all_bt_metrics.append(metrics)
        payloads[model] = (valid, equity, trades)
    bt_metrics = pd.DataFrame(all_bt_metrics)
    best = select_best_model(model_metrics, bt_metrics)
    signals, equity, trades = payloads[best]
    equity = benchmark_metrics(signals, equity)
    latest = signals.iloc[-1]

    intraday_result = analyze_intraday(stock_raw.get("intraday", pd.DataFrame()), signals, symbol, name)
    if not intraday_result.empty:
        save_csv(intraday_result, stock_data_dir / "intraday_analysis_5m.csv")

    merged_metrics = model_metrics.merge(
        bt_metrics[["model", "signal_win_rate", "total_return", "max_drawdown",
                    "trade_count", "win_rate", "profit_loss_ratio"]],
        on="model",
    )
    save_csv(merged_metrics, stock_output_dir / "model_results.csv")
    save_csv(coefficients, stock_output_dir / "model_coefficients.csv")
    save_csv(signals, stock_data_dir / "model_dataset.csv")
    save_csv(equity, stock_output_dir / "backtest_equity.csv")
    save_csv(trades, stock_output_dir / "backtest_trades.csv")
    save_csv(bt_metrics, stock_output_dir / "backtest_metrics.csv")
    create_charts(signals, equity, corr, model_metrics, stock_output_dir, name)
    report = create_report(
        signals, corr_sum, lag, model_metrics, bt_metrics, coefficients, best,
        stock_output_dir, name, symbol,
    )
    selected_coefficients = coefficients[coefficients["model"] == best]
    coefficient_map = dict(
        zip(selected_coefficients["variable"], selected_coefficients["coefficient"])
    )
    best_metrics = model_metrics.loc[model_metrics["model"] == best].iloc[0]
    registry = {
        "symbol": symbol, "name": name, "model": best,
        "features": MODEL_FEATURES[best],
        "intercept": float(coefficient_map.pop("intercept")),
        "coefficients": {k: float(v) for k, v in coefficient_map.items()},
        "base_close": float(merged.iloc[-1]["close"]),
        "previous_volume": float(merged.iloc[-1]["volume"]),
        "previous_turnover": float(merged.iloc[-1]["turnover"]),
        "previous_market_amount": float(merged.iloc[-1]["market_amount"]),
        "band_pct": float(latest["band_pct"]),
        "risk_level": str(latest["risk_level"]),
        "daily_fallback": {
            "actual_price": float(latest["close"]),
            "theoretical_price": float(latest["theoretical_price"]),
            "deviation_pct": float(latest["deviation_pct"]),
            "deviation_level": str(latest["deviation_level"]),
            "buy_zones": [float(latest[f"buy_zone_{i}"]) for i in range(1, 4)],
            "sell_zones": [float(latest[f"sell_zone_{i}"]) for i in range(1, 4)],
            "stop_loss_price": float(latest["stop_loss_price"]),
        },
        "metrics": {
            "r2": float(best_metrics["r2"]),
            "mae": float(best_metrics["mae"]),
            "rmse": float(best_metrics["rmse"]),
            "direction_accuracy": float(best_metrics["direction_accuracy"]),
        },
        "data_date": pd.Timestamp(merged.iloc[-1]["date"]).isoformat(),
    }
    summary = {
        "date": latest["date"], "symbol": symbol, "name": name,
        "daily_start": merged["date"].min(), "daily_end": merged["date"].max(),
        "daily_rows": len(merged), "analysis_start": signals["date"].min(),
        "analysis_rows": len(signals), "best_model": best,
        "actual_price": latest["close"], "theoretical_price": latest["theoretical_price"],
        "deviation_pct": latest["deviation_pct"], "deviation_level": latest["deviation_level"],
        "buy_signal": latest["buy_signal"], "sell_signal": latest["sell_signal"],
        "buy_zone_1": latest["buy_zone_1"], "buy_zone_2": latest["buy_zone_2"],
        "buy_zone_3": latest["buy_zone_3"], "sell_zone_1": latest["sell_zone_1"],
        "sell_zone_2": latest["sell_zone_2"], "sell_zone_3": latest["sell_zone_3"],
        "stop_loss_price": latest["stop_loss_price"], "risk_level": latest["risk_level"],
        "advice": operation_advice(latest), "report": str(report),
        **intraday_summary(intraday_result), "_registry": registry,
    }
    LOGGER.info("%s(%s) 完成：模型 %s，偏离 %.2f%%", name, symbol, best, latest["deviation_pct"] * 100)
    return summary


def _write_consolidated_report(summary: pd.DataFrame, output_dir: Path) -> Path:
    display = summary[
        ["symbol", "name", "daily_start", "daily_end", "daily_rows", "best_model",
         "analysis_start", "analysis_rows", "actual_price", "theoretical_price",
         "deviation_pct", "deviation_level",
         "risk_level", "advice", "intraday_end", "intraday_zone"]
    ].copy()
    display["deviation_pct"] = display["deviation_pct"].map(lambda x: f"{x:.2%}")
    content = f"""# 资本市场活跃度敏感股票横向分析

{display.to_markdown(index=False)}

## 数据口径

日线取最近十年或上市以来全部可得数据。指南针和财富趋势上市不足十年，因此其历史从上市后开始。分钟线仅保留公开接口实际可取得区间，不代表十年分钟历史。每只股票独立训练和选择模型参数。

## 风险提示

**{RISK_WARNING}**
"""
    path = output_dir / "multi_stock_summary_report.md"
    path.write_text(content, encoding="utf-8")
    return path


def run_pipeline(
    root: Path, start: str, end: str, force: bool = False,
    symbols: list[str] | None = None, fetch_minutes: bool = True,
) -> dict:
    data_dir, output_dir = ensure_dirs(root)
    setup_logging(output_dir)
    selected = symbols or list(STOCKS)
    unknown = sorted(set(selected) - set(STOCKS))
    if unknown:
        raise ValueError(f"不支持的股票代码: {unknown}")
    LOGGER.info("运行股票池 %s，区间 %s - %s", ",".join(selected), start, end)
    market_dir = data_dir / "market"
    market_dir.mkdir(parents=True, exist_ok=True)
    market = fetch_market_data(
        market_dir, start.replace("-", ""), end.replace("-", ""), force
    )
    summaries, registries, failures = [], {}, []
    for symbol in selected:
        try:
            result = run_single_stock(
                    root, symbol, STOCKS[symbol], market, start, end, force, fetch_minutes
                )
            registries[symbol] = result.pop("_registry")
            summaries.append(result)
        except Exception as exc:
            LOGGER.exception("%s(%s) 分析失败，其余股票继续", STOCKS[symbol]["name"], symbol)
            failures.append({"symbol": symbol, "error": str(exc)})
    if not summaries:
        raise RuntimeError(f"所有股票均分析失败: {failures}")
    summary = pd.DataFrame(summaries)
    save_csv(summary, output_dir / "multi_stock_summary.csv")
    registry_payload = {
        "schema_version": 1,
        "generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "data_date": str(summary["daily_end"].max()),
        "stocks": registries,
    }
    (output_dir / "model_registry.json").write_text(
        json.dumps(registry_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    alerts = build_alerts(summary)
    new_alerts = save_new_alerts(alerts, output_dir)
    report = _write_consolidated_report(summary, output_dir)
    LOGGER.warning(RISK_WARNING)
    return {
        "summary": summary, "alerts": alerts, "new_alerts": new_alerts,
        "report": report, "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(description="资本市场活跃度敏感股票相对价值分析")
    parser.add_argument("--start", default=(today - timedelta(days=365 * 10)).isoformat())
    parser.add_argument("--end", default=today.isoformat())
    parser.add_argument("--symbols", nargs="+", choices=list(STOCKS), default=list(STOCKS))
    parser.add_argument("--force", action="store_true", help="忽略缓存并重新获取")
    parser.add_argument("--no-intraday", action="store_true", help="跳过分钟线更新")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run_pipeline(
            Path(__file__).resolve().parent, args.start, args.end, args.force,
            args.symbols, not args.no_intraday,
        )
    except Exception:
        LOGGER.exception("运行失败")
        raise
