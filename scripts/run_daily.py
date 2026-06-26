"""Daily pre-market check. Sends email only if stop-loss or SPY correction fires."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sheets.client import get_sheet
from src.sheets.price_refresh import trigger_price_refresh
from src.sheets.reader import read_holdings, read_config
from src.sheets.writer import update_holdings, append_signal_log
from src.portfolio.calculator import compute_holdings, get_portfolio_breakdown
from src.portfolio.analyzer import analyze_health
from src.signals.tier1_macro import check_rotation_signals
from src.signals.tier2_rebalance import check_rebalance_signals
from src.signals.tier3_speculative import (
    check_deployment_signals,
    check_stop_loss_signals,
    check_take_profit_signals,
)
from src.signals.correction import check_correction_signal
from src.alerts.dispatcher import dispatch_daily
from src.utils.logger import get_logger
from scripts.process_trades import process_trades

logger = get_logger("run_daily")


def main():
    logger.info("=== Daily Portfolio Demon ===")

    sheet = get_sheet()

    try:
        process_trades(sheet)
    except Exception as e:
        logger.error("Trade processing failed: %s", e)

    trigger_price_refresh()
    config = read_config(sheet)
    holdings = read_holdings(sheet)

    holdings = compute_holdings(holdings, config)
    breakdown = get_portfolio_breakdown(holdings, config)
    health = analyze_health(holdings, config, breakdown)

    all_signals = []
    notes_parts = []

    try:
        all_signals.extend(check_rotation_signals(holdings, config))
    except Exception as e:
        logger.error("Tier 1 signals failed: %s", e)
        notes_parts.append(f"tier1_error: {e}")

    try:
        all_signals.extend(check_rebalance_signals(holdings, config, breakdown, health))
    except Exception as e:
        logger.error("Tier 2 signals failed: %s", e)
        notes_parts.append(f"tier2_error: {e}")

    deployment_signals = []
    try:
        deployment_signals = check_deployment_signals(holdings, config)
        all_signals.extend(deployment_signals)
        all_signals.extend(check_stop_loss_signals(holdings, config))
        all_signals.extend(check_take_profit_signals(holdings))
    except Exception as e:
        logger.error("Tier 3 signals failed: %s", e)
        notes_parts.append(f"tier3_error: {e}")

    try:
        correction = check_correction_signal(config)
        if correction:
            all_signals.append(correction)
    except Exception as e:
        logger.error("Correction check failed: %s", e)
        notes_parts.append(f"correction_error: {e}")

    try:
        update_holdings(sheet, holdings)
    except Exception as e:
        logger.error("Sheet update failed: %s", e)
        notes_parts.append(f"sheet_update_error: {e}")

    sent = dispatch_daily(all_signals, config, holdings, breakdown, health, deployment_signals)

    try:
        from src.sheets.price_refresh import get_spy_daily_change
        spy_change = get_spy_daily_change() or 0.0
        append_signal_log(
            sheet,
            run_type="daily",
            signals_fired=[{"type": s["type"], "symbol": s.get("symbol", "")} for s in all_signals],
            email_sent=sent,
            sp500_change_pct=spy_change,
            portfolio_equity_pct=breakdown["equity_pct"],
            portfolio_fund_pct=breakdown["fund_pct"],
            notes="; ".join(notes_parts),
        )
    except Exception as e:
        logger.error("Signal log failed: %s", e)

    logger.info("Daily run complete. Signals: %d, Email sent: %s", len(all_signals), sent)


if __name__ == "__main__":
    main()
