import time
import yfinance as yf
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("market.prices")

FIDELITY_FUNDS = {"FXAIX", "FSPSX", "FDGFX", "FXNAX", "FIPDX", "FZILX"}

_history_cache: dict[str, pd.DataFrame] = {}

BATCH_SIZE = 5
BATCH_DELAY = 12


def _extract_close(df: pd.DataFrame, symbol: str | None = None) -> pd.Series:
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        if symbol and symbol in close.columns:
            return close[symbol].dropna()
        return close.iloc[:, 0].dropna()
    return close.dropna()


def _download_batch(symbols: list[str], period: str = "3mo") -> bool:
    if not symbols:
        return False
    ticker_str = " ".join(symbols)
    try:
        df = yf.download(ticker_str, period=period, interval="1d", progress=False, threads=False)
    except Exception as e:
        logger.warning("Batch failed [%s]: %s", ", ".join(symbols), e)
        return False

    if df.empty:
        return False

    close = df["Close"]
    if isinstance(close, pd.Series):
        series = close.dropna()
        if not series.empty:
            _history_cache[symbols[0]] = df
            return True
        return False

    cached_any = False
    for sym in symbols:
        if sym not in close.columns:
            continue
        series = close[sym].dropna()
        if series.empty:
            continue
        try:
            sym_df = df.xs(sym, axis=1, level=1) if isinstance(df.columns, pd.MultiIndex) else df
            _history_cache[sym] = sym_df if not sym_df.empty else pd.DataFrame()
        except Exception:
            _history_cache[sym] = pd.DataFrame()
        cached_any = True

    return cached_any


def prefetch_history(symbols: list[str]) -> None:
    """Fetch 3-month history for 50d MA calculation. Small batches with long delays."""
    global _history_cache

    if not symbols:
        return

    all_symbols = list(set(symbols + ["SPY"]))
    batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]

    logger.info("Fetching history for %d symbols in %d batches (size %d, %ds delay)",
                len(all_symbols), len(batches), BATCH_SIZE, BATCH_DELAY)

    for i, batch in enumerate(batches):
        if i > 0:
            logger.info("Waiting %ds before batch %d...", BATCH_DELAY, i + 1)
            time.sleep(BATCH_DELAY)
        logger.info("Batch %d/%d: %s", i + 1, len(batches), " ".join(batch))
        success = _download_batch(batch)
        if not success:
            logger.warning("Batch %d failed — backing off 20s", i + 1)
            time.sleep(20)

    # Retry missing Fidelity mutual funds
    missing_funds = [s for s in symbols if s in FIDELITY_FUNDS and s not in _history_cache]
    for sym in missing_funds:
        time.sleep(BATCH_DELAY)
        logger.info("Retrying mutual fund %s", sym)
        _download_batch([sym], period="3mo")

    logger.info("History prefetch complete: %d/%d symbols", len(_history_cache), len(all_symbols))


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
