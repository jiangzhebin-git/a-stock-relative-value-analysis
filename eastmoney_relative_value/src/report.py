from pathlib import Path

import pandas as pd

from .config import MODEL_FEATURES, RISK_WARNING
from .deviation_signal import operation_advice


def _pct(value) -> str:
    return f"{float(value):.2%}"


def _table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def create_report(
    data: pd.DataFrame, corr_summary: pd.DataFrame, lag: pd.DataFrame,
    model_metrics: pd.DataFrame, bt_metrics: pd.DataFrame, coefficients: pd.DataFrame,
    best_model: str, output_dir: Path, stock_name: str = "东方财富", symbol: str = "300059",
) -> Path:
    latest = data.dropna(subset=["theoretical_price", "deviation_pct"]).iloc[-1]
    coef = coefficients[coefficients.model == best_model]
    formula_parts = [
        f"{r.coefficient:+.6f} × {r.variable}" for r in coef.itertuples() if r.variable != "intercept"
    ]
    intercept = coef.loc[coef.variable == "intercept", "coefficient"].iloc[0]
    metrics_display = model_metrics.copy()
    for col in ["r2", "mae", "rmse", "direction_accuracy"]:
        metrics_display[col] = metrics_display[col].map(lambda x: f"{x:.4f}")
    lag_best = lag.loc[lag.groupby("variable")["correlation"].apply(lambda s: s.abs().idxmax())]
    bt_display = bt_metrics.copy()
    for col in ["total_return", "annualized_return", "max_drawdown", "win_rate"]:
        bt_display[col] = bt_display[col].map(_pct)
    selected_bt = bt_metrics.loc[bt_metrics.model == best_model].iloc[0]
    stock_hold = data["close"].iloc[-1] / data["close"].iloc[0] - 1
    hs300_hold = data["hs300_close"].iloc[-1] / data["hs300_close"].iloc[0] - 1

    content = f"""# {stock_name}相对市场活跃度量化辅助分析报告

## 项目目标

判断{stock_name}（{symbol}）当前价格相对于 A 股整体市场、证券板块和市场成交活跃度是偏贵、合理还是偏便宜。本项目是相对价值辅助工具，不是确定性预测工具，也不执行交易。

## 数据来源与区间

- 数据来源：AkShare（东方财富公开行情接口）
- 清洗后区间：{data.date.min():%Y-%m-%d} 至 {data.date.max():%Y-%m-%d}
- 有效交易日：{len(data)}
- 价格口径：{stock_name}前复权日线；指数为日线收盘；成交额为沪深指数成交额之和
- 证券板块代理：中证全指证券公司指数（399975）

## 变量说明

模型目标为{stock_name}日收益率。候选变量包括上证、深证、创业板、沪深300、证券板块收益率，两市成交额变化率，以及个股自身成交量和换手率变化率。四组模型分别使用：

{chr(10).join(f"- 模型 {k}：{', '.join(v)}" for k, v in MODEL_FEATURES.items())}

## 相关性分析结果

{_table(corr_summary.round(4))}

相关性仅表示线性共变，不代表因果关系。证券板块与成交额变量是否更有解释力，应结合样本外模型增益判断。

## 滞后性分析结果

正滞后 N 日表示变量在 t-N 日与{stock_name} t 日收益的相关性。各变量绝对相关性最大的滞后如下：

{_table(lag_best.round(4))}

## 四组模型表现对比

指标均基于扩展窗口样本外预测：

{_table(metrics_display)}

## 最优模型选择理由

综合样本外 R²、MAE、RMSE、方向准确率、年化收益、最大回撤和盈亏表现，第一版选择 **模型 {best_model}**。综合排名降低了仅追逐单一高 R² 或单次高收益导致过拟合的风险。

## 理论价格模型公式

`theoretical_return = {intercept:.6f} {' '.join(formula_parts)}`

`theoretical_price = yesterday_close × (1 + theoretical_return)`

## 偏离指数与信号规则

`deviation_pct = (actual_price - theoretical_price) / theoretical_price`

- 大于 +5%：明显偏贵；+2% 至 +5%：偏贵
- -2% 至 +2%：合理
- -5% 至 -2%：偏便宜；低于 -5%：明显偏便宜
- 买卖观察信号另行过滤证券板块趋势、两市成交额、大盘趋势及个股量能
- 买卖三区和止损价由 ATR、20 日波动率生成，不使用单一固定比例

## 回测结果

信号在当日收盘后形成，下一交易日开盘执行；不包含手续费、滑点、涨跌停无法成交等约束。

{_table(bt_display)}

在相同样本区间，模型 {best_model} 策略总收益为 {_pct(selected_bt.total_return)}，
{stock_name}买入持有为 {_pct(stock_hold)}，沪深300买入持有为 {_pct(hs300_hold)}。
策略相对{stock_name}的收益差为 {_pct(selected_bt.total_return - stock_hold)}，
相对沪深300的收益差为 {_pct(selected_bt.total_return - hs300_hold)}。

## 当前结论

- 实际价格：**{latest.close:.2f} 元**
- 理论价格：**{latest.theoretical_price:.2f} 元**
- 偏离指数：**{_pct(latest.deviation_pct)}**
- 判断：**{latest.deviation_level}**
- 买入参考区间：{latest.buy_zone_3:.2f}–{latest.buy_zone_1:.2f} 元
- 卖出参考区间：{latest.sell_zone_1:.2f}–{latest.sell_zone_3:.2f} 元
- 止损参考价：{latest.stop_loss_price:.2f} 元
- 风险等级：**{latest.risk_level}**
- 操作建议：{operation_advice(latest)}

## 下一步开发建议

加入财报、公告事件、融资余额和涨跌停家数；加入手续费、滑点和涨跌停成交约束；执行滚动参数稳定性与市场状态分层检验；在人工确认界面中展示数据新鲜度和模型置信区间。

## 风险提示

**{RISK_WARNING}**
"""
    path = output_dir / f"{symbol}_relative_value_report.md"
    path.write_text(content, encoding="utf-8")
    return path
