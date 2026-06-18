from src.alerts.telegram_bot import send_telegram_message
from src.alerts.formatter import (
    format_weekly_digest,
    format_correction_alert,
    format_stop_loss_alert,
)
from src.utils.logger import get_logger

logger = get_logger("alerts.dispatcher")


def dispatch_weekly(holdings, config, breakdown, health, all_signals) -> bool:
    message = format_weekly_digest(holdings, config, breakdown, health, all_signals)
    return send_telegram_message(message)


def dispatch_correction(correction_signal, deployment_signals, config) -> bool:
    message = format_correction_alert(
        change_pct=correction_signal["sp500_change_pct"],
        cash=config["CASH_REMAINING"],
        opportunities=deployment_signals,
    )
    return send_telegram_message(message)


def dispatch_stop_loss(signal) -> bool:
    message = format_stop_loss_alert(signal)
    return send_telegram_message(message)


def dispatch_daily(all_signals, config, holdings, breakdown, health, deployment_signals) -> bool:
    sent = False

    # Immediate: stop-loss alerts
    stop_losses = [s for s in all_signals if s["type"] == "stop_loss"]
    for sl in stop_losses:
        if send_telegram_message(format_stop_loss_alert(sl)):
            sent = True

    # Immediate: correction alert
    correction = next((s for s in all_signals if s["type"] == "correction"), None)
    if correction:
        if dispatch_correction(correction, deployment_signals, config):
            sent = True

    if not sent:
        logger.info("Daily run: no immediate alerts — silent run")

    return sent
