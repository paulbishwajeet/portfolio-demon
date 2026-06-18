import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config.settings import (
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENT,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
    DRY_RUN,
)
from src.utils.logger import get_logger
from src.utils.retry import api_retry

logger = get_logger("alerts.email")


@api_retry
def _send_email(subject: str, body_text: str, body_html: str | None = None) -> bool:
    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT
    msg["Subject"] = subject

    msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())

    return True


def send_email(subject: str, body_text: str, body_html: str | None = None) -> bool:
    if DRY_RUN:
        logger.info("DRY RUN — would send email:\nSubject: %s\n%s", subject, body_text)
        return False

    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        logger.error("Email credentials not configured")
        return False

    try:
        _send_email(subject, body_text, body_html)
        logger.info("Email sent: %s (%d chars)", subject, len(body_text))
        return True
    except Exception as e:
        logger.error("Email send failed: %s", e)
        logger.info("Full message that failed:\nSubject: %s\n%s", subject, body_text)
        return False
