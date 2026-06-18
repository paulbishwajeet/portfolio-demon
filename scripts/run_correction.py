"""Intraday correction check — fires only if SPY drops >3%."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sheets.client import get_sheet
from src.sheets.reader import read_holdings, read_config
from src.sheets.writer import append_signal_log
from src.portfolio.calculator import compute_holdings, get_portfolio_breakdown
from src.signals.tier3_speculative import check_deployment_signals
from src.signals.correction import check_correction_signal
from src.alerts.dispatcher import dispatch_correction
from src.market.prices import get_spy_daily_change
from src.utils.logger import get_logger

logger = get_logger("run_correction")


def main():
    logger.info("=== Correction Check ===")

    sheet = get_sheet()
    config = read_config(sheet)

    correction = check_correction_signal(config)
    spy_change = get_spy_daily_change() or 0.0

    sent = False
    signals = []

    if correction:
        signals.append(correction)
        holdings = read_holdings(sheet)
        holdings = compute_holdings(holdings, config)
        deployment_signals = check_deployment_signals(holdings, config)
        signals.extend(deployment_signals)
        sent = dispatch_correction(correction, deployment_signals, config)
    else:
        logger.info("No correction detected (SPY change: %.2f%%)", spy_change)

    try:
        breakdown = get_portfolio_breakdown(
            read_holdings(sheet) if not correction else holdings, config
        )
        append_signal_log(
            sheet,
            run_type="correction",
            signals_fired=[{"type": s["type"], "symbol": s.get("symbol", "")} for s in signals],
            email_sent=sent,
            sp500_change_pct=spy_change,
            portfolio_equity_pct=breakdown["equity_pct"],
            portfolio_fund_pct=breakdown["fund_pct"],
        )
    except Exception as e:
        logger.error("Signal log failed: %s", e)

    logger.info("Correction check complete. Alert sent: %s", sent)


if __name__ == "__main__":
    main()
