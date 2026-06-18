from src.sheets.price_refresh import get_spy_daily_change
from src.utils.logger import get_logger

logger = get_logger("signals.correction")


def check_correction_signal(config: dict) -> dict | None:
    threshold = config["SP500_CORRECTION_THRESHOLD"]
    change = get_spy_daily_change()

    if change is None:
        logger.warning("Could not determine SPY daily change")
        return None

    logger.info("SPY daily change: %.2f%%", change)

    if change <= -threshold:
        return {
            "type": "correction",
            "severity": "red",
            "sp500_change_pct": round(change, 1),
            "cash_available": config["CASH_REMAINING"],
            "message": f"S&P 500 down {change:.1f}% today — correction threshold ({threshold}%) breached",
        }

    return None
