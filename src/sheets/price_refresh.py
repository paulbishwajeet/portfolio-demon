import requests

from config.settings import APPS_SCRIPT_URL
from src.utils.logger import get_logger

logger = get_logger("sheets.price_refresh")

TIMEOUT_SECONDS = 120


def trigger_price_refresh() -> bool:
    """Call the Google Apps Script web app to refresh prices in the sheet.
    Returns True if prices were refreshed successfully."""
    if not APPS_SCRIPT_URL:
        logger.warning("APPS_SCRIPT_URL not set — skipping price refresh")
        return False

    logger.info("Triggering price refresh via Apps Script...")
    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "ok":
            logger.info("Price refresh complete: %d updated, %d failed",
                        data.get("updated", 0), len(data.get("failed", [])))
            if data.get("failed"):
                logger.warning("Failed symbols: %s", ", ".join(data["failed"]))
            return True
        else:
            logger.error("Price refresh error: %s", data.get("message", "unknown"))
            return False
    except requests.exceptions.Timeout:
        logger.error("Price refresh timed out after %ds — sheet may have partial updates", TIMEOUT_SECONDS)
        return False
    except Exception as e:
        logger.error("Price refresh failed: %s", e)
        return False
