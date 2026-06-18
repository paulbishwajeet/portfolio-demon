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

EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "")
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
RUN_MODE = os.environ.get("RUN_MODE", "daily")
