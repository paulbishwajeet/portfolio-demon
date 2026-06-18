import requests

from config.settings import APPS_SCRIPT_URL
from src.utils.logger import get_logger

logger = get_logger("sheets.price_refresh")

TIMEOUT_SECONDS = 300

_moving_averages: dict[str, float] = {}
_spy_daily_change: float | None = None


def trigger_price_refresh() -> bool:
    """Call the Google Apps Script web app to refresh prices, MAs, and SPY change.
    Returns True if prices were refreshed successfully."""
    global _moving_averages, _spy_daily_change

    if not APPS_SCRIPT_URL:
        logger.warning("APPS_SCRIPT_URL not set — skipping price refresh")
        return False

    logger.info("Triggering price refresh via Apps Script...")
    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "ok":
            logger.info("Price refresh: %d updated, %d failed",
                        data.get("updated", 0), len(data.get("failed", [])))
            if data.get("failed"):
                logger.warning("Failed symbols: %s", ", ".join(data["failed"]))

            ma_data = data.get("moving_averages", {})
            _moving_averages = {k: float(v) for k, v in ma_data.items() if v is not None}
            logger.info("50d MA data received for %d symbols", len(_moving_averages))

            spy = data.get("spy_daily_change_pct")
            _spy_daily_change = float(spy) if spy is not None else None
            if _spy_daily_change is not None:
                logger.info("SPY daily change: %.2f%%", _spy_daily_change)

            return True
        else:
            logger.error("Price refresh error: %s", data.get("message", "unknown"))
            return False
    except requests.exceptions.Timeout:
        logger.error("Price refresh timed out after %ds", TIMEOUT_SECONDS)
        return False
    except Exception as e:
        logger.error("Price refresh failed: %s", e)
        return False


def get_moving_average(symbol: str) -> float | None:
    return _moving_averages.get(symbol)


def get_spy_daily_change() -> float | None:
    return _spy_daily_change
