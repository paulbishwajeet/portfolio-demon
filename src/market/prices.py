import time
import yfinance as yf
import pandas as pd

from src.utils.logger import get_logger

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


def _download_batch(symbols: list[str], period: str = "3mo") -> bool:
    """Download a small batch of symbols. Returns True if any data was cached."""
    if not symbols:
        return False

    ticker_str = " ".join(symbols)
    try:
        df = yf.download(ticker_str, period=period, interval="1d", progress=False, threads=False)
    except Exception as e:
        logger.warning("Batch download failed for %s: %s", symbols, e)
        return False

    if df.empty:
        return False

    close = df["Close"]

    # Single-symbol download returns a Series, not a multi-column DataFrame
    if isinstance(close, pd.Series):
        series = close.dropna()
        if not series.empty:
            sym = symbols[0]
            _price_cache[sym] = float(series.iloc[-1])
            _history_cache[sym] = df
            return True
        return False

    cached_any = False
    for sym in symbols:
        if sym not in close.columns:
            continue
        series = close[sym].dropna()
        if series.empty:
            continue
        _price_cache[sym] = float(series.iloc[-1])
        try:
            sym_df = df.xs(sym, axis=1, level=1) if isinstance(df.columns, pd.MultiIndex) else df
            _history_cache[sym] = sym_df if not sym_df.empty else pd.DataFrame()
        except Exception:
            _history_cache[sym] = pd.DataFrame()
        cached_any = True

    return cached_any


def prefetch_all(symbols: list[str]) -> None:
    """Download price history in small batches with delays to avoid rate limits."""
    global _price_cache, _history_cache

    if not symbols:
        return

    all_symbols = list(set(symbols + ["SPY"]))
    batch_size = 8
    batches = [all_symbols[i:i + batch_size] for i in range(0, len(all_symbols), batch_size)]

    logger.info("Fetching %d symbols in %d batches of %d", len(all_symbols), len(batches), batch_size)

    for i, batch in enumerate(batches):
        if i > 0:
            time.sleep(2)
        logger.info("Batch %d/%d: %s", i + 1, len(batches), " ".join(batch))
        _download_batch(batch)

    # Retry any Fidelity mutual funds that didn't come through
    missing_funds = [s for s in symbols if s in FIDELITY_FUNDS and s not in _history_cache]
    for sym in missing_funds:
        time.sleep(2)
        logger.info("Retrying mutual fund %s individually", sym)
        _download_batch([sym], period="3mo")

    logger.info("Prefetch complete: %d/%d symbols have history", len(_history_cache), len(all_symbols))


def get_current_price(symbol: str) -> float | None:
    if symbol in _price_cache:
        return _price_cache[symbol]
    return None


def get_history(symbol: str) -> pd.DataFrame:
    if symbol in _history_cache and not _history_cache[symbol].empty:
        return _history_cache[symbol]
    return pd.DataFrame()


def get_spy_daily_change() -> float | None:
    try:
        if "SPY" not in _history_cache or _history_cache["SPY"].empty:
            return None
        df = _history_cache["SPY"]
        series = _extract_close(df, "SPY")
        if len(series) < 2:
            return None
        today_close = float(series.iloc[-1])
        prev_close = float(series.iloc[-2])
        return (today_close - prev_close) / prev_close * 100
    except Exception as e:
        logger.error("Failed to get SPY daily change: %s", e)
        return None
