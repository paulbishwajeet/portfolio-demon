"""Set up Google Sheets formulas on computed columns in Holdings.

After running this, these columns auto-update whenever you change
deployed_amount or deployed_shares:
  F: planned_amount
  I: avg_cost_per_share
  Q: current_value
  R: pl_dollar
  S: pl_pct
  T: portfolio_weight_pct
  U: headroom_amount
  V: headroom_pct
  W: vs_plan_pct

Columns P (current_price), X (dip_score), Y (last_updated) are still
filled by the Python monitor — they need live market data.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from src.sheets.client import get_sheet
from src.utils.logger import get_logger

logger = get_logger("setup_formulas")

# Reference to TOTAL_IRA_VALUE in Portfolio_Config tab (row 2, col B)
TOTAL_IRA_REF = "Portfolio_Config!B2"


def setup_formulas():
    sheet = get_sheet()
    ws = sheet.worksheet("Holdings")
    all_data = ws.get_all_values()
    num_rows = len(all_data) - 1  # minus header

    if num_rows < 1:
        logger.error("No data rows found in Holdings")
        return

    logger.info("Setting formulas for %d holdings rows (rows 2-%d)", num_rows, num_rows + 1)

    cells_to_update = []

    for row in range(2, num_rows + 2):
        # F: planned_amount = planned_pct / 100 * TOTAL_IRA_VALUE
        cells_to_update.append(gspread.Cell(
            row, 6,
            f'=IF(E{row}="", 0, E{row}/100*{TOTAL_IRA_REF})'
        ))

        # I: avg_cost_per_share = deployed_amount / deployed_shares
        cells_to_update.append(gspread.Cell(
            row, 9,
            f'=IF(H{row}>0, G{row}/H{row}, 0)'
        ))

        # Q: current_value = current_price * deployed_shares
        cells_to_update.append(gspread.Cell(
            row, 17,
            f'=IF(AND(P{row}>0, H{row}>0), P{row}*H{row}, 0)'
        ))

        # R: pl_dollar = current_value - deployed_amount
        cells_to_update.append(gspread.Cell(
            row, 18,
            f'=IF(G{row}>0, Q{row}-G{row}, 0)'
        ))

        # S: pl_pct = pl_dollar / deployed_amount * 100
        cells_to_update.append(gspread.Cell(
            row, 19,
            f'=IF(G{row}>0, R{row}/G{row}*100, 0)'
        ))

        # T: portfolio_weight_pct = current_value / TOTAL_IRA_VALUE * 100
        cells_to_update.append(gspread.Cell(
            row, 20,
            f'=IF({TOTAL_IRA_REF}>0, Q{row}/{TOTAL_IRA_REF}*100, 0)'
        ))

        # U: headroom_amount = planned_amount - deployed_amount
        cells_to_update.append(gspread.Cell(
            row, 21,
            f'=F{row}-G{row}'
        ))

        # V: headroom_pct = headroom_amount / planned_amount * 100
        cells_to_update.append(gspread.Cell(
            row, 22,
            f'=IF(F{row}>0, U{row}/F{row}*100, 0)'
        ))

        # W: vs_plan_pct = portfolio_weight_pct - planned_pct
        cells_to_update.append(gspread.Cell(
            row, 23,
            f'=T{row}-E{row}'
        ))

    # Use value_input_option='USER_ENTERED' so Google Sheets interprets formulas
    ws.update_cells(cells_to_update, value_input_option='USER_ENTERED')
    logger.info("Set %d formulas across %d rows", len(cells_to_update), num_rows)

    # Format the computed columns as numbers
    logger.info("Formulas set! Computed columns now auto-update when you change deployed_amount or deployed_shares.")


if __name__ == "__main__":
    setup_formulas()
