"""Add dropdown validations to all restricted-value columns across all tabs."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sheets.client import get_sheet
from src.utils.logger import get_logger

logger = get_logger("setup_dropdowns")


def set_dropdown(sheet_id, ws_id, col_index, values, start_row=1, end_row=100):
    """Build a SetDataValidation request for a column range."""
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
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in values],
                },
                "showCustomUi": True,
                "strict": True,
            },
        }
    }


def setup_dropdowns():
    sheet = get_sheet()
    spreadsheet_id = sheet.id

    # Get worksheet IDs
    ws_ids = {}
    for ws in sheet.worksheets():
        ws_ids[ws.title] = ws.id

    requests = []

    # ── Holdings tab ──
    h_id = ws_ids["Holdings"]

    # D: category (col index 3)
    requests.append(set_dropdown(spreadsheet_id, h_id, 3, [
        "core_fund", "quality_stock", "speculative",
        "new_defensive", "existing_addition", "trim_exit",
    ]))

    # M: status (col index 12)
    requests.append(set_dropdown(spreadsheet_id, h_id, 12, [
        "active", "new", "watch", "trim", "exit",
    ]))

    # N: cycle_alignment (col index 13)
    requests.append(set_dropdown(spreadsheet_id, h_id, 13, [
        "positive", "negative", "neutral",
    ]))

    # ── Portfolio_Config tab ──
    pc_id = ws_ids["Portfolio_Config"]

    # CYCLE_PHASE is in row 7 (0-indexed: row 6-7), col B (index 1)
    # Find the exact row for CYCLE_PHASE
    pc_ws = sheet.worksheet("Portfolio_Config")
    pc_data = pc_ws.get_all_values()
    cycle_row = None
    for i, row in enumerate(pc_data):
        if row[0] == "CYCLE_PHASE":
            cycle_row = i
            break

    if cycle_row is not None:
        requests.append(set_dropdown(spreadsheet_id, pc_id, 1, [
            "EARLY", "MID", "LATE", "RECESSION",
        ], start_row=cycle_row, end_row=cycle_row + 1))
        logger.info("CYCLE_PHASE dropdown at row %d", cycle_row + 1)

    # ── Trade_Entry tab ──
    te_id = ws_ids["Trade_Entry"]

    # C: action (col index 2)
    requests.append(set_dropdown(spreadsheet_id, te_id, 2, [
        "BUY", "SELL", "TRIM",
    ]))

    # G: reason (col index 6)
    requests.append(set_dropdown(spreadsheet_id, te_id, 6, [
        "dip buy", "rebalance", "rotation", "stop-loss",
        "take-profit", "new position", "other",
    ]))

    # B: symbol — pull from Holdings column A
    # Use a formula-based validation referencing Holdings!A2:A100
    requests.append({
        "setDataValidation": {
            "range": {
                "sheetId": te_id,
                "startRowIndex": 1,
                "endRowIndex": 50,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_RANGE",
                    "values": [{"userEnteredValue": "=Holdings!A2:A100"}],
                },
                "showCustomUi": True,
                "strict": True,
            },
        }
    })

    # ── Transactions tab ──
    tx_id = ws_ids["Transactions"]

    # C: action (col index 2)
    requests.append(set_dropdown(spreadsheet_id, tx_id, 2, [
        "BUY", "SELL", "TRIM",
    ]))

    # G: reason (col index 6)
    requests.append(set_dropdown(spreadsheet_id, tx_id, 6, [
        "dip buy", "rebalance", "rotation", "stop-loss",
        "take-profit", "new position", "other",
    ]))

    # H: cycle_phase_at_trade (col index 7)
    requests.append(set_dropdown(spreadsheet_id, tx_id, 7, [
        "EARLY", "MID", "LATE", "RECESSION",
    ]))

    # Execute all validation requests
    sheet.batch_update({"requests": requests})
    logger.info("Set %d dropdown validations across all tabs", len(requests))


if __name__ == "__main__":
    setup_dropdowns()
