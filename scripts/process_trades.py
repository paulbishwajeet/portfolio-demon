"""Process pending trades from the Trade_Entry tab.

Workflow:
  1. You enter trades in the Trade_Entry tab (symbol, shares, price)
  2. Run this script — it updates Holdings and logs to Transactions
  3. Formulas in Holdings auto-recalculate everything else

Trade_Entry columns:
  A: date          (YYYY-MM-DD)
  B: symbol        (must match a symbol in Holdings)
  C: action        (BUY / SELL / TRIM)
  D: shares        (number of shares in this trade)
  E: price_per_share (price you paid/received per share)
  F: total_amount  (formula: =D*E, auto-calculated)
  G: reason        (dip buy / rebalance / rotation / stop-loss / other)
  H: status        (pending / processed — script processes 'pending' rows)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from src.sheets.client import get_sheet
from src.utils.logger import get_logger
from src.utils.date_utils import iso_now

logger = get_logger("process_trades")

TRADE_ENTRY_HEADERS = [
    "date", "symbol", "action", "shares",
    "price_per_share", "total_amount", "reason", "status",
]


def ensure_trade_entry_tab(sheet: gspread.Spreadsheet) -> gspread.Worksheet:
    try:
        ws = sheet.worksheet("Trade_Entry")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Trade_Entry", rows=50, cols=8)
        ws.append_row(TRADE_ENTRY_HEADERS)
        # Add the total_amount formula hint in row 2
        ws.update_acell("F2", '=IF(D2>0, D2*E2, 0)')
        ws.update_acell("H2", "pending")
        logger.info("Created Trade_Entry tab")
    return ws


def process_trades(sheet=None):
    if sheet is None:
        sheet = get_sheet()

    # Ensure Trade_Entry tab exists
    te_ws = ensure_trade_entry_tab(sheet)
    te_rows = te_ws.get_all_values()

    if len(te_rows) <= 1:
        logger.info("No trades to process")
        return

    # Find pending trades
    pending = []
    for i, row in enumerate(te_rows[1:], start=2):  # skip header, 1-indexed in sheet
        if len(row) < 8:
            row.extend([""] * (8 - len(row)))
        status = row[7].strip().lower()
        if status == "pending":
            pending.append((i, row))

    if not pending:
        logger.info("No pending trades found")
        return

    logger.info("Found %d pending trades", len(pending))

    # Load Holdings
    h_ws = sheet.worksheet("Holdings")
    h_data = h_ws.get_all_values()
    h_headers = h_data[0]

    # Build symbol -> row index map
    sym_col = h_headers.index("symbol")
    deployed_amt_col = h_headers.index("deployed_amount")
    deployed_shares_col = h_headers.index("deployed_shares")

    symbol_rows = {}
    for i, row in enumerate(h_data[1:], start=2):
        if row[sym_col]:
            symbol_rows[row[sym_col].strip().upper()] = i

    # Load Transactions tab
    try:
        tx_ws = sheet.worksheet("Transactions")
    except gspread.WorksheetNotFound:
        tx_ws = sheet.add_worksheet(title="Transactions", rows=100, cols=8)
        tx_ws.append_row(["date", "symbol", "action", "shares", "price_per_share", "total_amount", "reason", "cycle_phase_at_trade"])

    # Read config for cycle phase and current cash balance
    config_ws = sheet.worksheet("Portfolio_Config")
    config_rows = config_ws.get_all_values()
    cycle_phase = "LATE"
    cash_remaining = 0.0
    cash_row_idx = None
    for i, row in enumerate(config_rows):
        if row[0] == "CYCLE_PHASE":
            cycle_phase = row[1]
        if row[0] == "CASH_REMAINING":
            try:
                cash_remaining = float(row[1].replace(",", ""))
            except (ValueError, TypeError):
                cash_remaining = 0.0
            cash_row_idx = i + 1  # 1-indexed for gspread

    logger.info("Current SPAXX/cash balance: $%.2f", cash_remaining)

    # Process each pending trade
    holdings_updates = []  # (row, col, value) tuples
    tx_rows = []
    te_status_updates = []
    net_cash_change = 0.0

    for te_row_idx, row in pending:
        trade_date = row[0].strip()
        symbol = row[1].strip().upper()
        action = row[2].strip().upper()
        try:
            shares = float(row[3].replace(",", ""))
        except (ValueError, AttributeError):
            logger.error("Row %d: invalid shares '%s'", te_row_idx, row[3])
            continue
        try:
            price = float(row[4].replace(",", "").replace("$", ""))
        except (ValueError, AttributeError):
            logger.error("Row %d: invalid price '%s'", te_row_idx, row[4])
            continue

        total_amount = round(shares * price, 2)
        reason = row[6].strip() if len(row) > 6 else ""

        if symbol not in symbol_rows:
            logger.error("Row %d: symbol '%s' not found in Holdings", te_row_idx, symbol)
            continue

        h_row_idx = symbol_rows[symbol]
        h_row = h_data[h_row_idx - 1]  # 0-indexed in h_data

        current_deployed_amt = float(h_row[deployed_amt_col].replace(",", "") or "0")
        current_deployed_shares = float(h_row[deployed_shares_col].replace(",", "") or "0")

        if action == "BUY":
            new_deployed_amt = round(current_deployed_amt + total_amount, 2)
            new_deployed_shares = round(current_deployed_shares + shares, 6)
            net_cash_change -= total_amount  # money leaves SPAXX
        elif action in ("SELL", "TRIM"):
            new_deployed_amt = round(current_deployed_amt - total_amount, 2)
            new_deployed_shares = round(current_deployed_shares - shares, 6)
            net_cash_change += total_amount  # money returns to SPAXX
            if new_deployed_shares < 0:
                logger.error("Row %d: selling more shares than held for %s", te_row_idx, symbol)
                net_cash_change -= total_amount  # undo
                continue
        else:
            logger.error("Row %d: unknown action '%s'", te_row_idx, action)
            continue

        logger.info(
            "%s %s: %s %.4f shares @ $%.2f = $%.2f | deployed: $%.2f -> $%.2f, shares: %.4f -> %.4f",
            action, symbol, trade_date, shares, price, total_amount,
            current_deployed_amt, new_deployed_amt,
            current_deployed_shares, new_deployed_shares,
        )

        # Queue Holdings update (G and H columns, 1-indexed)
        holdings_updates.append(gspread.Cell(h_row_idx, deployed_amt_col + 1, new_deployed_amt))
        holdings_updates.append(gspread.Cell(h_row_idx, deployed_shares_col + 1, new_deployed_shares))

        # Update in-memory data for subsequent trades on same symbol
        h_data[h_row_idx - 1][deployed_amt_col] = str(new_deployed_amt)
        h_data[h_row_idx - 1][deployed_shares_col] = str(new_deployed_shares)

        # Queue Transaction log row
        tx_rows.append([trade_date, symbol, action, shares, price, total_amount, reason, cycle_phase])

        # Queue Trade_Entry status update to 'processed'
        te_status_updates.append(gspread.Cell(te_row_idx, 8, "processed"))

    # Apply all updates
    if holdings_updates:
        h_ws.update_cells(holdings_updates)
        logger.info("Updated %d cells in Holdings", len(holdings_updates))

    for tx_row in tx_rows:
        tx_ws.append_row(tx_row)
    if tx_rows:
        logger.info("Logged %d transactions", len(tx_rows))

    if te_status_updates:
        te_ws.update_cells(te_status_updates)
        logger.info("Marked %d trades as processed", len(te_status_updates))

    # Update CASH_REMAINING (SPAXX balance) in Portfolio_Config
    if net_cash_change != 0 and cash_row_idx is not None:
        new_cash = round(cash_remaining + net_cash_change, 2)
        config_ws.update_cell(cash_row_idx, 2, str(new_cash))
        logger.info("SPAXX balance: $%.2f -> $%.2f (%+.2f)", cash_remaining, new_cash, net_cash_change)
    elif net_cash_change != 0:
        logger.warning("Could not update CASH_REMAINING — row not found in Portfolio_Config")

    logger.info("Trade processing complete!")


if __name__ == "__main__":
    process_trades()
