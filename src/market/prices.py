import yfinance as yf
import pandas as pd

from src.utils.logger import get_logger
from src.utils.retry import api_retry

logger = get_logger("market.prices")

# Fidelity mutual fund tickers may need this prefix in some contexts
MUTF_PREFIX = "MUTF_US:"
FIDELITY_FUNDS = {"FXAIX", "FSPSX", "FDGFX", "FXNAX", "FIPDX", "FZILX"}


@api_retry
def get_current_price(symbol: str) -> float | None:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        if price and price > 0:
            return float(price)
    except Exception:
        pass

    # Fallback: try history
    try:
        hist = yf.download(symbol, period="5d", interval="1d", progress=False)
        if not hist.empty:
            close = hist["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            return float(close.dropna().iloc[-1])
    except Exception as e:
        logger.warning("Failed to get price for %s: %s", symbol, e)

    return None


@api_retry
def get_history(symbol: str, period: str = "60d", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if not df.empty:
            return df
    except Exception:
        pass

    if symbol in FIDELITY_FUNDS:
        logger.info("Retrying %s as mutual fund with extended period", symbol)
        try:
            df = yf.download(symbol, period="3mo", interval="1d", progress=False)
            if not df.empty:
                return df
        except Exception as e:
            logger.warning("Mutual fund fallback failed for %s: %s", symbol, e)

    return pd.DataFrame()


def get_bulk_prices(symbols: list[str]) -> dict[str, float | None]:
    prices = {}
    for symbol in symbols:
        prices[symbol] = get_current_price(symbol)
    return prices


@api_retry
def get_spy_daily_change() -> float | None:
    try:
        hist = yf.download("SPY", period="5d", interval="1d", progress=False)
        if hist.empty or len(hist) < 2:
            return None
        close = hist["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna()
        if len(close) < 2:
            return None
        today_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        return (today_close - prev_close) / prev_close * 100
    except Exception as e:
        logger.error("Failed to get SPY daily change: %s", e)
        return None
