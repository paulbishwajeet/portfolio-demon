import pandas as pd

from src.market.prices import get_history
from src.utils.logger import get_logger

logger = get_logger("market.indicators")


def get_moving_average(symbol: str, window: int = 50) -> float | None:
    df = get_history(symbol, period="60d")
    if df.empty:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    if len(close) < window:
        logger.warning("%s: only %d data points, need %d for MA", symbol, len(close), window)
        if len(close) >= 20:
            return float(close.mean())
        return None
    return float(close.tail(window).mean())


def get_dip_score(current_price: float, ma_50: float) -> float:
    if not ma_50 or ma_50 == 0:
        return 0.0
    return (current_price - ma_50) / ma_50 * 100


def get_52w_high_low(symbol: str) -> tuple[float | None, float | None]:
    df = get_history(symbol, period="1y")
    if df.empty:
        return None, None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    if close.empty:
        return None, None
    return float(close.max()), float(close.min())
