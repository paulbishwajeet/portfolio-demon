import gspread
from google.oauth2.service_account import Credentials

from config.settings import get_google_credentials_info, GOOGLE_SHEET_ID
from src.utils.logger import get_logger
from src.utils.retry import api_retry

logger = get_logger("sheets.client")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@api_retry
def get_sheet() -> gspread.Spreadsheet:
    creds_info = get_google_credentials_info()
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    logger.info("Connected to Google Sheet: %s", sheet.title)
    return sheet
