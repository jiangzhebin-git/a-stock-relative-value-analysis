import logging
from pathlib import Path

import numpy as np
import pandas as pd


def setup_logging(output_dir: Path) -> None:
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(output_dir / "run.log", encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def finite_or(value: float, default: float = 0.0) -> float:
    return float(value) if np.isfinite(value) else default


def annualized_return(total_return: float, periods: int, annual_days: int = 252) -> float:
    if periods <= 0 or total_return <= -1:
        return 0.0
    return (1 + total_return) ** (annual_days / periods) - 1

