from src.alerts.email_sender import send_email
from src.alerts.formatter import (
    format_weekly_digest,
    format_correction_alert,
    format_stop_loss_alert,
)
from src.sheets.price_refresh import get_refresh_status
from src.utils.logger import get_logger

logger = get_logger("alerts.dispatcher")


def _build_data_warnings() -> list[str]:
    warnings = []
    status = get_refresh_status()

    if not status["ran"]:
        warnings.append(f"Price refresh did not run: {status['error']}")
        warnings.append("Prices may be stale — verify before acting")
    elif not status["ok"]:
        warnings.append(f"Price refresh failed: {status['error']}")
        warnings.append("Prices may be stale — verify before acting")
    elif status["failed"]:
        warnings.append(f"Price refresh failed for: {', '.join(status['failed'])}")

    return warnings


def dispatch_weekly(holdings, config, breakdown, health, all_signals) -> bool:
    warnings = _build_data_warnings()
    subject, plain, html = format_weekly_digest(
        holdings, config, breakdown, health, all_signals, data_warnings=warnings,
    )
    return send_email(subject, plain, html)


def dispatch_correction(correction_signal, deployment_signals, config) -> bool:
    subject, plain, html = format_correction_alert(
        change_pct=correction_signal["sp500_change_pct"],
        cash=config["CASH_REMAINING"],
        opportunities=deployment_signals,
    )
    return send_email(subject, plain, html)


def dispatch_stop_loss(signal) -> bool:
    subject, plain, html = format_stop_loss_alert(signal)
    return send_email(subject, plain, html)


def dispatch_daily(all_signals, config, holdings, breakdown, health, deployment_signals) -> bool:
    sent = False

    stop_losses = [s for s in all_signals if s["type"] == "stop_loss"]
    for sl in stop_losses:
        subject, plain, html = format_stop_loss_alert(sl)
        if send_email(subject, plain, html):
            sent = True

    correction = next((s for s in all_signals if s["type"] == "correction"), None)
    if correction:
        if dispatch_correction(correction, deployment_signals, config):
            sent = True

    if not sent:
        logger.info("Daily run: no immediate alerts — silent run")

    return sent
