import time
import yfinance as yf
import pandas as pd

from src.utils.logger import get_logger
from src.utils.retry import api_retry

logger = get_logger("market.prices")

FIDELITY_FUNDS = {"FXAIX", "FSPSX", "FDGFX", "FXNAX", "FIPDX", "FZILX"}

_price_cache: dict[str, float] = {}
_history_cache: dict[str, pd.DataFrame] = {}


def _extract_close(df: pd.DataFrame, symbol: str | None = None) -> pd.Series:
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        if symbol and symbol in close.columns:
            return close[symbol].dropna()
        return close.iloc[:, 0].dropna()
    return close.dropna()


def prefetch_all(symbols: list[str], period: str = "3mo") -> None:
    """Batch-download price history for all symbols in one request to avoid rate limits."""
    global _price_cache, _history_cache

    if not symbols:
        return

    # Include SPY for correction checks
    all_symbols = list(set(symbols + ["SPY"]))
    ticker_str = " ".join(all_symbols)

    logger.info("Batch downloading %d symbols", len(all_symbols))
    try:
        df = yf.download(ticker_str, period=period, interval="1d", progress=False, threads=True)
    except Exception as e:
        logger.error("Batch download failed: %s — falling back to individual", e)
        return

    if df.empty:
        logger.warning("Batch download returned empty data")
        return

    close = df["Close"]
    if isinstance(close, pd.Series):
        # Single symbol case
        sym = all_symbols[0] if len(all_symbols) == 1 else None
        if sym:
            series = close.dropna()
            if not series.empty:
                _price_cache[sym] = float(series.iloc[-1])
                _history_cache[sym] = df
        return

    for sym in all_symbols:
        if sym not in close.columns:
            continue
        series = close[sym].dropna()
        if series.empty:
            continue
        _price_cache[sym] = float(series.iloc[-1])
        sym_df = df.xs(sym, axis=1, level=1) if isinstance(df.columns, pd.MultiIndex) else df
        _history_cache[sym] = sym_df if not sym_df.empty else pd.DataFrame()

    # Retry Fidelity mutual funds individually if missing
    for sym in symbols:
        if sym in FIDELITY_FUNDS and sym not in _price_cache:
            logger.info("Retrying %s individually (mutual fund)", sym)
            time.sleep(1)
            try:
                fund_df = yf.download(sym, period="3mo", interval="1d", progress=False)
                if not fund_df.empty:
                    series = _extract_close(fund_df, sym)
                    if not series.empty:
                        _price_cache[sym] = float(series.iloc[-1])
                        _history_cache[sym] = fund_df
            except Exception as e:
                logger.warning("Mutual fund retry failed for %s: %s", sym, e)

    logger.info("Prefetch complete: %d/%d symbols cached", len(_price_cache), len(all_symbols))


def get_current_price(symbol: str) -> float | None:
    if symbol in _price_cache:
        return _price_cache[symbol]

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        if price and price > 0:
            _price_cache[symbol] = float(price)
            return float(price)
    except Exception:
        pass

    try:
        hist = yf.download(symbol, period="5d", interval="1d", progress=False)
        if not hist.empty:
            series = _extract_close(hist, symbol)
            if not series.empty:
                price = float(series.iloc[-1])
                _price_cache[symbol] = price
                return price
    except Exception as e:
        logger.warning("Failed to get price for %s: %s", symbol, e)

    return None


def get_history(symbol: str, period: str = "60d", interval: str = "1d") -> pd.DataFrame:
    if symbol in _history_cache and not _history_cache[symbol].empty:
        return _history_cache[symbol]

    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if not df.empty:
            _history_cache[symbol] = df
            return df
    except Exception:
        pass

    if symbol in FIDELITY_FUNDS:
        logger.info("Retrying %s as mutual fund with extended period", symbol)
        try:
            df = yf.download(symbol, period="3mo", interval="1d", progress=False)
            if not df.empty:
                _history_cache[symbol] = df
                return df
        except Exception as e:
            logger.warning("Mutual fund fallback failed for %s: %s", symbol, e)

    return pd.DataFrame()


def get_spy_daily_change() -> float | None:
    try:
        if "SPY" in _history_cache and not _history_cache["SPY"].empty:
            df = _history_cache["SPY"]
        else:
            df = yf.download("SPY", period="5d", interval="1d", progress=False)

        if df.empty or len(df) < 2:
            return None
        series = _extract_close(df, "SPY")
        if len(series) < 2:
            return None
        today_close = float(series.iloc[-1])
        prev_close = float(series.iloc[-2])
        return (today_close - prev_close) / prev_close * 100
    except Exception as e:
        logger.error("Failed to get SPY daily change: %s", e)
        return None
