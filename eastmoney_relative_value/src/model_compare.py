from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import MODEL_FEATURES


def expanding_oos_predict(
    df: pd.DataFrame, features: list[str], min_train: int = 252, refit_every: int = 20
) -> tuple[pd.Series, object]:
    n = len(df)
    if n < 120:
        raise ValueError("有效样本少于 120 个交易日，无法进行可靠的时间序列验证")
    min_train = min(max(60, min_train), max(60, n // 2))
    predictions = pd.Series(np.nan, index=df.index, dtype=float)
    model = None
    for start in range(min_train, n, refit_every):
        end = min(start + refit_every, n)
        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        model.fit(df.loc[: start - 1, features], df.loc[: start - 1, "stock_return"])
        predictions.loc[start : end - 1] = model.predict(df.loc[start : end - 1, features])
    final_model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    final_model.fit(df[features], df["stock_return"])
    return predictions, final_model


def _effective_coefficients(model, features: list[str]) -> tuple[float, dict[str, float]]:
    scaler, ridge = model.steps[0][1], model.steps[1][1]
    coefs = ridge.coef_ / scaler.scale_
    intercept = ridge.intercept_ - np.sum(ridge.coef_ * scaler.mean_ / scaler.scale_)
    return float(intercept), dict(zip(features, coefs.astype(float)))


def compare_models(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics, coefficients = [], []
    predictions = df[["date", "stock_return", "close"]].copy()
    for name, features in MODEL_FEATURES.items():
        pred, model = expanding_oos_predict(df, features)
        predictions[f"pred_{name}"] = pred
        valid = pred.notna()
        actual, forecast = df.loc[valid, "stock_return"], pred[valid]
        metrics.append({
            "model": name,
            "r2": r2_score(actual, forecast),
            "mae": mean_absolute_error(actual, forecast),
            "rmse": mean_squared_error(actual, forecast) ** 0.5,
            "direction_accuracy": ((actual >= 0) == (forecast >= 0)).mean(),
            "oos_samples": int(valid.sum()),
        })
        intercept, coefs = _effective_coefficients(model, features)
        coefficients.append({"model": name, "variable": "intercept", "coefficient": intercept})
        coefficients.extend(
            {"model": name, "variable": key, "coefficient": value}
            for key, value in coefs.items()
        )
    return pd.DataFrame(metrics), predictions, pd.DataFrame(coefficients)


def select_best_model(metrics: pd.DataFrame, backtest_metrics: pd.DataFrame | None = None) -> str:
    score = metrics.set_index("model").copy()
    score["rank_score"] = (
        score["r2"].rank(ascending=False)
        + score["mae"].rank()
        + score["rmse"].rank()
        + score["direction_accuracy"].rank(ascending=False)
    )
    if backtest_metrics is not None and not backtest_metrics.empty:
        bt = backtest_metrics.set_index("model")
        score["rank_score"] += (
            bt["annualized_return"].rank(ascending=False)
            + bt["max_drawdown"].abs().rank()
            + bt["profit_factor"].replace(np.inf, np.nan).fillna(bt["profit_factor"].max()).rank(
                ascending=False
            )
        )
    return str(score["rank_score"].idxmin())

