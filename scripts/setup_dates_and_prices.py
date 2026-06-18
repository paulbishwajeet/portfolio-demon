"""Add date pickers to date columns and GOOGLEFINANCE live prices to Holdings."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from src.sheets.client import get_sheet
from src.utils.logger import get_logger

logger = get_logger("setup_dates_prices")

FIDELITY_MUTUAL_FUNDS = {"FXAIX", "FSPSX", "FDGFX", "FXNAX", "FIPDX", "FZILX"}


def set_date_validation(ws_id, col_index, start_row=1, end_row=100):
    return {
        "setDataValidation": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": col_index,
                "endColumnIndex": col_index + 1,
            },
            "rule": {
                "condition": {
                    "type": "DATE_IS_VALID",
                },
                "strict": False,
            },
        }
    }


def set_date_format(ws_id, col_index, start_row=1, end_row=100):
    return {
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": col_index,
                "endColumnIndex": col_index + 1,
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {
                        "type": "DATE",
                        "pattern": "yyyy-mm-dd",
                    }
                }
            },
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def setup():
    sheet = get_sheet()

    ws_ids = {}
    for ws in sheet.worksheets():
        ws_ids[ws.title] = ws.id

    requests = []

    # ── Date pickers ──

    # Trade_Entry: column A (index 0) — date
    te_id = ws_ids["Trade_Entry"]
    requests.append(set_date_validation(te_id, 0))
    requests.append(set_date_format(te_id, 0))

    # Transactions: column A (index 0) — date
    tx_id = ws_ids["Transactions"]
    requests.append(set_date_validation(tx_id, 0))
    requests.append(set_date_format(tx_id, 0))

    # Holdings: column Y (index 24) — last_updated (display as date)
    h_id = ws_ids["Holdings"]
    requests.append(set_date_format(h_id, 24))

    # Execute date validations
    sheet.batch_update({"requests": requests})
    logger.info("Set date pickers on Trade_Entry.date, Transactions.date, Holdings.last_updated")

    # ── GOOGLEFINANCE live prices in Holdings column P ──

    h_ws = sheet.worksheet("Holdings")
    all_data = h_ws.get_all_values()
    num_rows = len(all_data) - 1

    if num_rows < 1:
        logger.error("No data rows in Holdings")
        return

    cells = []
    for row_idx in range(2, num_rows + 2):
        symbol = all_data[row_idx - 1][0].strip()
        if not symbol:
            continue

        if symbol in FIDELITY_MUTUAL_FUNDS:
            ticker_ref = f'MUTF:{symbol}'
        else:
            ticker_ref = symbol

        # GOOGLEFINANCE with IFERROR fallback — returns blank if ticker not found
        formula = f'=IFERROR(GOOGLEFINANCE("{ticker_ref}", "price"), "")'
        cells.append(gspread.Cell(row_idx, 16, formula))  # column P = 16

    h_ws.update_cells(cells, value_input_option='USER_ENTERED')
    logger.info("Set GOOGLEFINANCE formulas for %d symbols in column P (current_price)", len(cells))
    logger.info("Done! Prices update live in the sheet now.")


if __name__ == "__main__":
    setup()
