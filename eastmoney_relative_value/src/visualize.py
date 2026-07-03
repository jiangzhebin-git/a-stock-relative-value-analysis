from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")
_font_path = Path("C:/Windows/Fonts/msyh.ttc")
if _font_path.exists():
    font_manager.fontManager.addfont(str(_font_path))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(_font_path)).get_name()
else:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def create_charts(
    data: pd.DataFrame, equity: pd.DataFrame, corr: pd.DataFrame,
    metrics: pd.DataFrame, output_dir: Path, stock_name: str = "东方财富"
) -> None:
    plt.figure(figsize=(14, 6))
    plt.plot(data.date, data.close, label="实际价格")
    plt.plot(data.date, data.theoretical_price, label="理论价格", alpha=.8)
    plt.legend(); plt.title(f"{stock_name}实际价格 vs 理论价格")
    _save(output_dir / "actual_vs_theoretical.png")

    plt.figure(figsize=(14, 5))
    plt.plot(data.date, data.deviation_pct * 100)
    plt.axhspan(-2, 2, alpha=.15, color="green"); plt.axhline(5, color="red", ls="--")
    plt.axhline(-5, color="blue", ls="--"); plt.ylabel("%"); plt.title("偏离指数")
    _save(output_dir / "deviation_timeseries.png")

    plt.figure(figsize=(14, 6))
    plt.plot(data.date, data.close, color="black", lw=1)
    buys, sells = data[data.buy_signal], data[data.sell_signal]
    plt.scatter(buys.date, buys.close, marker="^", color="green", label="买入观察", s=30)
    plt.scatter(sells.date, sells.close, marker="v", color="red", label="卖出观察", s=30)
    plt.legend(); plt.title("价格与偏离信号")
    _save(output_dir / "signals.png")

    plt.figure(figsize=(14, 6))
    plt.plot(equity.date, equity.equity, label="策略")
    plt.plot(equity.date, equity.stock_buy_hold, label=f"{stock_name}买入持有")
    plt.legend(); plt.title(f"策略净值 vs {stock_name}")
    _save(output_dir / "equity_vs_stock.png")

    plt.figure(figsize=(14, 6))
    plt.plot(equity.date, equity.equity, label="策略")
    plt.plot(equity.date, equity.hs300_buy_hold, label="沪深300")
    plt.legend(); plt.title("策略净值 vs 沪深300")
    _save(output_dir / "equity_vs_hs300.png")

    plt.figure(figsize=(11, 9))
    sns.heatmap(corr, cmap="RdBu_r", center=0, annot=True, fmt=".2f")
    plt.title("变量相关性热力图")
    _save(output_dir / "correlation_heatmap.png")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, col in zip(axes, ["r2", "mae", "rmse"]):
        sns.barplot(data=metrics, x="model", y=col, ax=ax)
        ax.set_title(col.upper())
    _save(output_dir / "model_comparison.png")

    plt.figure(figsize=(10, 5))
    sns.histplot(data["deviation_pct"].dropna() * 100, bins=60, kde=True)
    plt.xlabel("偏离指数 (%)"); plt.title("偏离指数分布")
    _save(output_dir / "deviation_distribution.png")
