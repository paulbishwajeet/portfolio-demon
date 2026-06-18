"""Manual trigger — runs the selected mode based on RUN_MODE env var."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import RUN_MODE
from src.utils.logger import get_logger

logger = get_logger("run_manual")


def main():
    mode = RUN_MODE.lower()
    logger.info("Manual run: mode=%s", mode)

    if mode == "daily":
        from scripts.run_daily import main as run
        run()
    elif mode == "weekly":
        from scripts.run_weekly import main as run
        run()
    elif mode == "correction_check":
        from scripts.run_correction import main as run
        run()
    elif mode == "full_report":
        from scripts.run_weekly import main as run
        run()
    elif mode == "seed_sheet":
        from scripts.seed_sheet import seed
        seed()
    else:
        logger.error("Unknown mode: %s", mode)
        sys.exit(1)


if __name__ == "__main__":
    main()
