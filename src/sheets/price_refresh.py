import requests

from config.settings import APPS_SCRIPT_URL
from src.utils.logger import get_logger

logger = get_logger("sheets.price_refresh")

TIMEOUT_SECONDS = 300

_moving_averages: dict[str, float] = {}
_prev_prices: dict[str, float] = {}
_spy_daily_change: float | None = None
_refresh_status: dict = {"ran": False, "ok": False, "updated": 0, "failed": [], "error": ""}


def trigger_price_refresh() -> bool:
    global _moving_averages, _prev_prices, _spy_daily_change, _refresh_status

    if not APPS_SCRIPT_URL:
        _refresh_status = {"ran": False, "ok": False, "updated": 0, "failed": [],
                           "error": "APPS_SCRIPT_URL not configured"}
        logger.warning("APPS_SCRIPT_URL not set — skipping price refresh")
        return False

    logger.info("Triggering price refresh via Apps Script...")
    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "ok":
            failed = data.get("failed", [])
            updated = data.get("updated", 0)
            logger.info("Price refresh: %d updated, %d failed", updated, len(failed))
            if failed:
                logger.warning("Failed symbols: %s", ", ".join(failed))

            prev_data = data.get("prev_prices", {})
            _prev_prices = {k: float(v) for k, v in prev_data.items() if v is not None}
            logger.info("Previous close prices received for %d symbols", len(_prev_prices))

            ma_data = data.get("moving_averages", {})
            _moving_averages = {k: float(v) for k, v in ma_data.items() if v is not None}
            logger.info("50d MA data received for %d symbols", len(_moving_averages))

            spy = data.get("spy_daily_change_pct")
            _spy_daily_change = float(spy) if spy is not None else None
            if _spy_daily_change is not None:
                logger.info("SPY daily change: %.2f%%", _spy_daily_change)

            _refresh_status = {"ran": True, "ok": True, "updated": updated,
                               "failed": failed, "error": ""}
            return True
        else:
            msg = data.get("message", "unknown error")
            _refresh_status = {"ran": True, "ok": False, "updated": 0,
                               "failed": [], "error": msg}
            logger.error("Price refresh error: %s", msg)
            return False
    except requests.exceptions.Timeout:
        _refresh_status = {"ran": True, "ok": False, "updated": 0,
                           "failed": [], "error": f"Timed out after {TIMEOUT_SECONDS}s"}
        logger.error("Price refresh timed out after %ds", TIMEOUT_SECONDS)
        return False
    except Exception as e:
        _refresh_status = {"ran": True, "ok": False, "updated": 0,
                           "failed": [], "error": str(e)}
        logger.error("Price refresh failed: %s", e)
        return False


def get_prev_price(symbol: str) -> float | None:
    return _prev_prices.get(symbol)


def get_moving_average(symbol: str) -> float | None:
    return _moving_averages.get(symbol)


def get_spy_daily_change() -> float | None:
    return _spy_daily_change


def get_refresh_status() -> dict:
    return _refresh_status
