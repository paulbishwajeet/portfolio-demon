import asyncio
from telegram import Bot

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN
from src.utils.logger import get_logger
from src.utils.retry import api_retry

logger = get_logger("alerts.telegram")

MAX_MESSAGE_LENGTH = 4096


def _split_message(text: str) -> list[str]:
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    parts = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


@api_retry
async def _send_message_async(text: str) -> bool:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    parts = _split_message(text)
    for part in parts:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=part,
            parse_mode="Markdown",
        )
    return True


def send_telegram_message(text: str) -> bool:
    if DRY_RUN:
        logger.info("DRY RUN — would send Telegram message:\n%s", text)
        return False

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not configured")
        return False

    try:
        asyncio.run(_send_message_async(text))
        logger.info("Telegram message sent (%d chars)", len(text))
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        logger.info("Full message that failed to send:\n%s", text)
        return False
