import os
import json
from dotenv import load_dotenv

load_dotenv()


def get_google_credentials_info():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    if os.path.isfile(raw):
        with open(raw) as f:
            return json.load(f)
    return json.loads(raw)


GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
RUN_MODE = os.environ.get("RUN_MODE", "daily")
