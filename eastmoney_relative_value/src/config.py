from pathlib import Path

RISK_WARNING = (
    "本模型仅基于历史数据和统计关系，用于辅助分析，不构成投资建议。"
    "市场可能受到政策、财报、流动性、突发事件、监管变化、公司基本面变化等影响，"
    "模型存在失效风险。任何买入、卖出或挂单操作都需要人工确认。"
)

STOCKS = {
    "300059": {"name": "东方财富", "exchange": "sz", "listed": "2010-03-19"},
    "300033": {"name": "同花顺", "exchange": "sz", "listed": "2009-12-25"},
    "300803": {"name": "指南针", "exchange": "sz", "listed": "2019-11-18"},
    "688318": {"name": "财富趋势", "exchange": "sh", "listed": "2020-04-27"},
}

INDEX_CODES = {
    "sh_return": "000001",
    "sz_return": "399001",
    "cyb_return": "399006",
    "hs300_return": "000300",
    "broker_return": "399975",
}

MODEL_FEATURES = {
    "A": ["sh_return", "sz_return", "cyb_return", "hs300_return"],
    "B": ["sh_return", "sz_return", "cyb_return", "hs300_return", "broker_return"],
    "C": [
        "sh_return", "sz_return", "cyb_return", "hs300_return",
        "broker_return", "market_amount_change",
    ],
    "D": [
        "sh_return", "sz_return", "cyb_return", "hs300_return",
        "broker_return", "market_amount_change", "stock_volume_change",
        "stock_turnover_change",
    ],
}

CORRELATION_FEATURES = MODEL_FEATURES["D"]
LAGS = [0, 1, 2, 3, 5, 10]


def ensure_dirs(root: Path) -> tuple[Path, Path]:
    data_dir, output_dir = root / "data", root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, output_dir
