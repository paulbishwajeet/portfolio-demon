from datetime import time
from src.utils.date_utils import now_et, today_et, is_trading_day

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def is_market_open() -> bool:
    if not is_trading_day():
        return False
    current = now_et().time()
    return MARKET_OPEN <= current <= MARKET_CLOSE


def is_market_hours() -> bool:
    return is_market_open()


def get_market_status() -> str:
    if not is_trading_day():
        return "closed (non-trading day)"
    current = now_et().time()
    if current < MARKET_OPEN:
        return "pre-market"
    elif current > MARKET_CLOSE:
        return "after-hours"
    return "open"
